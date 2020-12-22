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
from collections import abc as abcoll
import typing

import jinja2

from . import _context
from . import _types

if typing.TYPE_CHECKING:  # pragma: no cover
    from . import _engine


class Result:
    """A result of a task."""

    def __init__(
        self,
        results: typing.Mapping[str, typing.Any],
        failure: typing.Optional[str] = None,
        skipped: bool = False,
    ):
        self.__dict__.update(results)
        self.succeeded = failure is None
        self.failed = not self.succeeded
        self.failure = failure
        self.skipped = skipped


class When:
    """A when clause."""

    __slots__ = ('engine', 'definition')

    def __init__(
        self,
        engine: '_engine.Engine',
        definition: typing.Union[str, typing.List[str]],
    ):
        if isinstance(definition, str):
            definition = [definition]
        self.definition = definition
        self.engine = engine

    def __call__(self, context: '_context.Context') -> bool:
        """Check the condition."""
        return all(self.engine.environment.evaluate_code(expr, context)
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

    _KNOWN_PARAMETERS = frozenset(
        ['name', 'when', 'ignore_errors', 'register', 'loop'])

    _VALID_TYPES = (str, int, float, list)

    def __init__(
        self,
        engine: '_engine.Engine',
        params: typing.Union[
            typing.Dict[str, _types.JsonType],
            typing.List[_types.JsonType],
            None
        ],
        name: str,
        when: typing.Optional[When] = None,
        ignore_errors: bool = False,
        register: typing.Optional[str] = None,
        loop: typing.Union[str, list, None] = None,
    ):
        if (self.singleton_param is not None
                and self.singleton_param not in self.required_params
                and self.singleton_param not in self.optional_params
                and not self.free_form):
            raise TypeError("The singleton parameter must be either "
                            "a required or an optional parameter")

        for spec in (self.required_params, self.optional_params):
            if any(item is not None and item not in self._VALID_TYPES
                   for item in spec.values()):
                raise TypeError(
                    "Acceptable types for required/optional params are %s"
                    % ', '.join(x.__name__ for x in self._VALID_TYPES))

        self.engine = engine
        self.name = name
        self.when = when
        self.ignore_errors = ignore_errors
        self.register = register
        self.loop = loop
        if params is None:
            params = {}
        elif (isinstance(params, abcoll.Mapping)
              and not all(isinstance(key, str) for key in params)):
            raise _types.InvalidDefinition(
                f"Parameters for task {self.name} must have string keys")
        elif not isinstance(params, abcoll.Mapping):
            if self.singleton_param is None:
                raise _types.InvalidDefinition(
                    f"Task {self.name} accepts an object, not {params}")
            params = {self.singleton_param: params}
        self.params: typing.Mapping[str, typing.Any] = params

    @classmethod
    def load(
        cls,
        name: str,
        definition: typing.Dict[str, typing.Any],
        engine: '_engine.Engine',
    ) -> 'Task':
        """Load a task from its definition."""
        params = definition[name]
        top_level = {key: value for key, value in definition.items()
                     if key != name}

        when = top_level.pop('when', None)
        if when is not None:
            when = When(engine, when)

        ignore_errors = top_level.pop('ignore_errors', False)
        if not isinstance(ignore_errors, bool):
            raise _types.InvalidDefinition(
                "The ignore_errors parameter must be a boolean for task "
                f"{name}, got {ignore_errors}")

        register = top_level.pop('register', None)
        if register is not None and not isinstance(register, str):
            raise _types.InvalidDefinition(
                "The register parameter must be a string "
                f"for task {name}, got {register}")

        display_name = top_level.pop('name', None)
        if display_name is not None and not isinstance(display_name, str):
            raise _types.InvalidDefinition(
                "The name parameter must be a string "
                f"for task {name}, got {display_name}")

        loop = top_level.pop('loop', None)
        if loop is not None and not isinstance(loop, (str, list)):
            raise _types.InvalidDefinition(
                "The loop parameter must be a template or a list "
                f"for task {name}, got {loop}")

        if top_level:
            raise _types.InvalidDefinition(
                f"Unknown top-level parameters {', '.join(top_level)} "
                f"for task {name}")

        return cls(engine, params, display_name or name,
                   when, ignore_errors, register, loop)

    def validate(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: _context.Context,
    ) -> None:
        """Validate the passed parameters.

        The call may modify the parameters in-place, e.g. to apply type
        conversion.
        """
        known = dict(self.required_params, **self.optional_params)

        unknown = set(params).difference(known)
        if not self.free_form and unknown:
            raise _types.InvalidDefinition(
                "parameter(s) not recognized: %s"
                % ', '.join("'%s'" % item for item in unknown))

        missing = set(self.required_params).difference(params)
        if missing:
            raise _types.InvalidDefinition(
                "parameter(s) required: %s"
                % ', '.join("'%s'" % item for item in missing))

        if not params and not self.allow_empty:
            raise _types.InvalidDefinition(
                "at least one of %s is required"
                % ', '.join("'%s'" % item for item in self.optional_params))

        for name, type_ in known.items():
            if type_ is None:
                continue

            try:
                params[name] = type_(params[name])
            except KeyError:
                continue
            except (TypeError, ValueError, jinja2.TemplateError) as exc:
                raise _types.InvalidDefinition(
                    f"invalid value for parameter '{name}': {exc}")

    def __call__(self, context: _context.Context) -> None:
        """Check conditions and execute the task in the context."""
        if self.loop is None:
            result = self._execute_one(context)
            if self.register is not None:
                context[self.register] = result
        else:
            loop = self.engine.environment.evaluate_recursive(self.loop,
                                                              context)
            results = [self._execute_one(context, item)
                       for item in loop]
            if self.register is not None:
                context[self.register] = {"results": results}

    def _execute_one(self, context: _context.Context,
                     item: typing.Any = None) -> Result:
        """One iteration of a loop or a single execution."""
        if self.loop is not None:
            context = context.copy()
            context["item"] = item

        try:
            if self.when is not None and not self.when(context):
                self.engine.logger.debug("Task %s is skipped", self.name)
                return Result({}, skipped=True)
        except Exception as exc:
            raise _types.ExecutionFailed(
                f"Failed to evaluate condition for {self.name}. "
                f"{exc.__class__.__name__}: {exc}")

        # We need a Namespace to be able to evaluate parameters during
        # validation.
        params = _context.Namespace(
            self.engine.environment, context, self.params)

        try:
            self.validate(params, context)
            values = self.execute(params, context)
            if values is not None and not isinstance(values, abcoll.Mapping):
                raise RuntimeError("a task must return None or a mapping, "
                                   f"got {values}")
        except Exception as exc:
            if self.ignore_errors:
                self.engine.logger.warning("Task %s failed: %s (ignoring)",
                                           self.name, exc)
                return Result({}, f"{exc.__class__.__name__}: {exc}")
            else:
                if isinstance(exc, _types.Aborted):
                    msg = f"Execution aborted: {exc}"
                else:
                    msg = (f"Failed to execute task {self.name}. "
                           f"{exc.__class__.__name__}: {exc}")
                raise _types.ExecutionFailed(msg)
        else:
            return Result(values or {})

    @abc.abstractmethod
    def execute(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: _context.Context,
    ) -> typing.Optional[typing.Mapping[str, typing.Any]]:
        """Execute the task.

        :returns: The value stored as a result in ``register`` is set.
        """
