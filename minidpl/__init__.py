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
import logging
import typing

from jinja2 import nativetypes  # type: ignore
from jinja2 import sandbox  # type: ignore


class Environment(sandbox.Environment):  # type: ignore
    """A templating environment."""

    code_generator_class = nativetypes.NativeCodeGenerator
    template_class = nativetypes.NativeTemplate


DictType = typing.Dict[str, typing.Any]


JsonType = typing.Union[
    DictType,
    typing.List,
    str,
    int,
    bool,
    None
]


ParamsType = typing.Dict[str, typing.Union[
    typing.Dict[str, JsonType],
    typing.List[JsonType],
    None
]]


class Error(Exception):
    """Base class for all errors."""


class InvalidScript(Error, TypeError):
    """The script definition is invalid."""


class InvalidDefinition(Error, ValueError):
    """A definition of an action or condition is invalid."""


class UnknownAction(InvalidDefinition):
    """An action is not known."""


class When:
    """A when clause."""

    def __init__(
        self,
        engine: 'Engine',
        definition: typing.Union[str, typing.List[str]],
    ):
        if isinstance(definition, str):
            definition = [definition]
        self.definition = definition
        self.engine = engine

    def __call__(self, context: typing.Any) -> bool:
        """Check the condition."""
        return all(self.engine._evaluate(expr, context)
                   for expr in self.definition)


class Result:

    def __init__(
        self,
        result: typing.Any,
        failure: typing.Optional[str] = None,
    ):
        self.succeeded = failure is None
        self.failed = not self.succeeded
        self.failure = failure
        self.result = result


class Action(metaclass=abc.ABCMeta):
    """An abstract base class for an action."""

    required_params: typing.Dict[str, typing.Type] = {}
    """A mapping with required parameters."""

    optional_params: typing.Dict[str, typing.Type] = {}
    """A mapping with optional parameters."""

    list_param: typing.Optional[str] = None
    """A name for the parameter to store if the input is a list."""

    free_form: bool = False
    """Whether this action accepts any arguments.

    Validation for known arguments is still run, and required parameters are
    still required.
    """

    def __init__(
        self,
        engine: 'Engine',
        params: ParamsType,
        name: typing.Optional[str] = None,
        when: typing.Optional[When] = None,
        ignore_errors: bool = False,
        register: typing.Optional[str] = None,
    ):
        if (self.list_param is not None
                and self.list_param not in self.required_params
                and self.list_param not in self.optional_params
                and not self.free_form):
            raise RuntimeError("List parameters must be either a required or "
                               "an optional parameter")

        self.engine = engine
        self._params = params
        self.name = name
        self.when = when
        self.ignore_errors = ignore_errors
        self.register = register
        self._known = set(self.required_params).union(self.optional_params)
        self.validate()

    def validate(self) -> typing.Dict[str, typing.Any]:
        """Validate the passed parameters."""
        params = self._params

        if isinstance(params, list):
            if self.list_param is None:
                raise InvalidDefinition(f"Action {self.name} does not accept "
                                        "a list")
            params = {self.list_param: params}
        elif params is None:
            params = {}

        unknown = set(params).difference(self._known)
        if not self.free_form and unknown:
            raise InvalidDefinition("Parameters %s are not recognized"
                                    % ', '.join(unknown))

        result = {}
        missing = []

        for name, type_ in self.required_params.items():
            try:
                value = params[name]
            except KeyError:
                missing.append(name)
            else:
                try:
                    result[name] = type_(value)
                except (TypeError, ValueError) as exc:
                    raise InvalidDefinition(
                        f"Invalid value for parameter {name} of action "
                        f"{self.name}: {exc}")

        if missing:
            raise InvalidDefinition("Parameters %s are required for action %s",
                                    ','.join(missing), self.name)

        for name, type_ in self.optional_params.items():
            try:
                value = params[name]
            except KeyError:
                continue

            try:
                result[name] = type_(value)
            except (TypeError, ValueError) as exc:
                raise InvalidDefinition(
                    f"Invalid value for parameter {name} of action "
                    f"{self.name}: {exc}")

        return result

    def __call__(self, context: typing.Any) -> None:
        """Check conditions and execute the action in the context."""
        if self.when is not None and not self.when(context):
            self.engine.logger.debug("Action %s is skipped", self.name)

        params = self.validate()

        try:
            value = self.execute(params, context)
        except Exception as exc:
            if self.ignore_errors:
                self.engine.logger.warning("Action %s failed: %s (ignoring)",
                                           self.name, exc)
                result = Result(None, f"{exc.__class__.__name__}: {exc}")
            else:
                self.engine.logger.error("Action %s failed: %s",
                                         self.name, exc)
                raise
        else:
            result = Result(value)

        if self.register is not None:
            self.engine.set_var(self.register, result)

    @abc.abstractmethod
    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: typing.Any
    ) -> JsonType:
        """Execute the action.

        :returns: The value stored as a result in ``register`` is set.
        """


class Script:
    """A prepared script."""

    def __init__(
        self,
        engine: 'Engine',
        source: DictType,
    ) -> None:
        """Create a new script.

        :param engine: An `Engine`.
        :param source: A list of actions to execute.
        """
        self.engine = engine
        self.source = source
        tasks = source.get('tasks')
        if not tasks:
            raise InvalidScript('At least one task is required')
        elif not isinstance(tasks, list):
            raise InvalidScript(f'Tasks must be a list, got {tasks}')
        self.tasks = [engine._load_action(task) for task in tasks]

    def __call__(self, context: typing.Any) -> None:
        """Execute the script."""
        for item in self.tasks:
            item(context)


_KNOWN_PARAMETERS = frozenset(['name', 'when', 'ignore_errors', 'register'])


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        actions: typing.Dict[str, typing.Type[Action]],
        namespace: typing.Optional[typing.Dict[str, typing.Any]] = None,
        logger_name: str = __name__,
    ) -> None:
        """Create a new engine.

        :param actions: Mapping of actions to their implementations.
        :raises: ValueError on conflicting actions.
        """
        conflict = set(actions).intersection(_KNOWN_PARAMETERS)
        if conflict:
            raise ValueError('Actions %s conflict with built-in parameters'
                             % ', '.join(conflict))
        self.actions = actions
        self.logger = logging.getLogger(logger_name)
        self.namespace = namespace or {}
        self.environment = Environment()

    def execute(
        self,
        source: typing.Union[typing.List[DictType], DictType],
        context: typing.Any,
    ) -> None:
        """Execute a script.

        :param source: Script source code in JSON format.
        :param context: An application-specific object.
        :return: A `Script` object for execution.
        """
        self.prepare(source)(context)

    def prepare(
        self,
        source: typing.Union[typing.List[DictType], DictType],
    ) -> Script:
        """Prepare a script for execution.

        :param source: Script source code in JSON format.
        :return: A `Script` object for execution.
        """
        if isinstance(source, list):
            source = {'tasks': source}

        return Script(self, source)

    def set_var(self, name: str, value: typing.Any):
        """Set a variable."""
        self.namespace[name] = value

    def _load_action(self, definition: DictType) -> Action:
        """Load an action from the definition.

        :param definition: JSON definition of an action.
        :return: An `Action`
        """
        matching = set(definition).intersection(self.actions)
        if not matching:
            raise UnknownAction("Action defined by one of %s is not known"
                                % ','.join(definition))
        elif len(matching) > 1:
            raise InvalidDefinition("Item with keys %s is ambiguous"
                                    % ','.join(matching))

        name = matching.pop()
        action = self.actions[name]
        params = definition[name]
        if not isinstance(params, (list, dict)):
            raise InvalidDefinition(f"Parameters for action {name} must be a "
                                    f"list or an object, got {params}")
        elif isinstance(params, dict) and not all(isinstance(key, str)
                                                  for key in params):
            raise InvalidDefinition(f"Parameters for action {name} must "
                                    "have string keys")
        # We have checked compliance above
        params = typing.cast(ParamsType, params)

        top_level = {key: value for key, value in definition.items()
                     if key != name}
        when = top_level.pop('when', None)
        if when is not None:
            when = When(self, when)

        ignore_errors = top_level.pop('ignore_errors', False)
        if not isinstance(ignore_errors, bool):
            raise InvalidDefinition("The ignore_errors parameter must be "
                                    f"a boolean for action {name}, "
                                    f"got {ignore_errors}")

        register = top_level.pop('register', None)
        if register is not None and not isinstance(register, str):
            raise InvalidDefinition("The register parameter must be a string "
                                    f"for action {name}, got {register}")

        display_name = top_level.pop('name', None)
        if display_name is not None and not isinstance(display_name, str):
            raise InvalidDefinition("The name parameter must be a string "
                                    f"for action {name}, got {display_name}")

        return action(self, params, display_name,
                      when, ignore_errors, register)

    def _evaluate(self, expr: str, context: typing.Any) -> typing.Any:
        """Evaluate an expression."""
        return self.environment.from_string(expr, self.namespace).render()
