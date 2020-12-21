# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import abc
import typing

from . import _types

if typing.TYPE_CHECKING:
    from . import _engine


class Result:
    """A result of a task."""

    def __init__(
        self,
        result: typing.Any,
        failure: typing.Optional[str] = None,
    ):
        self.succeeded = failure is None
        self.failed = not self.succeeded
        self.failure = failure
        self.result = result


class When:
    """A when clause."""

    def __init__(
        self,
        engine: '_engine.Engine',
        definition: typing.Union[str, typing.List[str]],
    ):
        if isinstance(definition, str):
            definition = [definition]
        self.definition = definition
        self.engine = engine

    def __call__(self, context: '_engine.Context') -> bool:
        """Check the condition."""
        return all(self.engine._evaluate(expr, context)
                   for expr in self.definition)


class Task(metaclass=abc.ABCMeta):
    """An abstract base class for a task."""

    required_params: typing.Dict[str, typing.Optional[typing.Type]] = {}
    """A mapping with required parameters."""

    optional_params: typing.Dict[str, typing.Optional[typing.Type]] = {}
    """A mapping with optional parameters."""

    singleton_param: typing.Optional[str] = None
    """A name for the parameter to store if the input is not an object."""

    free_form: bool = False
    """Whether this task accepts any arguments.

    Validation for known arguments is still run, and required parameters are
    still required.
    """

    allow_empty: bool = True
    """If no parameters are required, whether to allow empty input."""

    def __init__(
        self,
        engine: '_engine.Engine',
        params: _types.ParamsType,
        name: str,
        when: typing.Optional[When] = None,
        ignore_errors: bool = False,
        register: typing.Optional[str] = None,
    ):
        if (self.singleton_param is not None
                and self.singleton_param not in self.required_params
                and self.singleton_param not in self.optional_params
                and not self.free_form):
            raise TypeError("The singleton parameter must be either "
                            "a required or an optional parameter")

        self.engine = engine
        self.name = name
        self.when = when
        self.ignore_errors = ignore_errors
        self.register = register
        self._known = set(self.required_params).union(self.optional_params)
        self.params = self.validate(params)

    def validate(
        self,
        params: _types.ParamsType
    ) -> typing.Dict[str, typing.Any]:
        """Validate the passed parameters."""
        if params is None:
            params = {}
        elif not isinstance(params, dict):
            if self.singleton_param is None:
                raise _types.InvalidDefinition(
                    f"Task {self.name} accepts an object, not {params}")
            params = {self.singleton_param: params}

        unknown = set(params).difference(self._known)
        if not self.free_form and unknown:
            raise _types.InvalidDefinition("Parameters %s are not recognized"
                                           % ', '.join(unknown))

        result = {}
        missing = []

        for name, type_ in self.required_params.items():
            try:
                value = params[name]
            except KeyError:
                missing.append(name)
            else:
                if type_ is None:
                    result[name] = value
                    continue

                try:
                    result[name] = type_(value)
                except (TypeError, ValueError) as exc:
                    raise _types.InvalidDefinition(
                        f"Invalid value for parameter {name} of task "
                        f"{self.name}: {exc}")

        if missing:
            raise _types.InvalidDefinition(
                "Parameters %s are required for task %s",
                ','.join(missing), self.name)

        for name, type_ in self.optional_params.items():
            try:
                value = params[name]
            except KeyError:
                continue

            if type_ is None:
                result[name] = value
                continue

            try:
                result[name] = type_(value)
            except (TypeError, ValueError) as exc:
                raise _types.InvalidDefinition(
                    f"Invalid value for parameter {name} of task "
                    f"{self.name}: {exc}")

        if not result and not self.allow_empty:
            raise _types.InvalidDefinition("At least one of %s is required"
                                           % ', '.join(self.optional_params))

        return result

    def _evaluate_params(self, params, context: '_engine.Context'):
        if isinstance(params, dict):
            result = {}
            for key, value in params.items():
                if isinstance(key, str):
                    key = self.engine._evaluate(key, context)
                value = self._evaluate_params(value, context)
                result[key] = value
            return result
        elif isinstance(params, list):
            return [self._evaluate_params(item, context) for item in params]
        elif isinstance(params, str):
            return self.engine._evaluate(params, context)
        else:
            return params

    def __call__(self, context: '_engine.Context') -> None:
        """Check conditions and execute the task in the context."""
        if self.when is not None and not self.when(context):
            self.engine.logger.debug("Task %s is skipped", self.name)

        try:
            params = self._evaluate_params(self.params, context)
        except Exception as exc:
            raise _types.ExecutionFailed(
                f"Failed to evaluate parameters for {self.name}. "
                f"{exc.__class__.__name__}: {exc}")

        try:
            value = self.execute(params, context)
        except Exception as exc:
            if self.ignore_errors:
                self.engine.logger.warning("Task %s failed: %s (ignoring)",
                                           self.name, exc)
                result = Result(None, f"{exc.__class__.__name__}: {exc}")
            else:
                raise
        else:
            result = Result(value)

        if self.register is not None:
            context[self.register] = result

    @abc.abstractmethod
    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context',
    ) -> typing.Any:
        """Execute the task.

        :returns: The value stored as a result in ``register`` is set.
        """


class Block(Task):
    """Grouping of tasks."""

    required_params = {"tasks": list}

    singleton_param = "tasks"

    def validate(
        self,
        params: _types.ParamsType
    ) -> typing.Dict[str, typing.Any]:
        tasks = super().validate(params)["tasks"]
        tasks = [self.engine._load_task(task) for task in tasks]
        return {"tasks": tasks}

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context',
    ) -> None:
        for task in params["tasks"]:
            task(context)


class Fail(Task):
    """Fail the execution."""

    required_params = {'msg': str}

    singleton_param = 'msg'

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context',
    ) -> None:
        raise _types.ExecutionFailed(f"{self.name} aborted: {params['msg']}")


class Log(Task):
    """Log something."""

    optional_params = {
        key: str for key in ("debug", "info", "warning", "error")}

    allow_empty = False

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context'
    ) -> None:
        for key, value in params.items():
            getattr(self.engine.logger, key)(value)


class Return(Task):
    """Return a value to the caller."""

    optional_params = {'result': None}

    singleton_param = 'result'

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context',
    ) -> None:
        raise _types.FinishScript(params.get('result'))


class Vars(Task):
    """Set some variables."""

    free_form = True

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_engine.Context'
    ) -> None:
        for key, value in params.items():
            context[key] = value
