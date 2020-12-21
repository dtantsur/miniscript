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

import logging
import typing

from jinja2 import nativetypes  # type: ignore
from jinja2 import sandbox  # type: ignore

from . import _actions
from . import _types


class Environment(sandbox.Environment):  # type: ignore
    """A templating environment."""

    code_generator_class = nativetypes.NativeCodeGenerator
    template_class = nativetypes.NativeTemplate


_BUILTINS: typing.Dict[str, typing.Type[_actions.Action]] = {
    "block": _actions.Block,
    "fail": _actions.Fail,
    "log": _actions.Log,
    "return": _actions.Return,
    "vars": _actions.Vars,
}


class Context(dict):
    """A context of an execution."""

    __slots__ = ()


class Script:
    """A prepared script."""

    def __init__(
        self,
        engine: 'Engine',
        source: _types.SourceType,
    ) -> None:
        """Create a new script.

        :param engine: An `Engine`.
        :param source: A source definition or a list of actions to execute.
        """
        if isinstance(source, list):
            source = {'tasks': source}

        self.engine = engine
        self.source = source

        tasks = source.get('tasks')
        if not tasks:
            raise _types.InvalidScript('At least one task is required')
        elif not isinstance(tasks, list):
            raise _types.InvalidScript(f'Tasks must be a list, got {tasks}')

        unknown = [x for x in source if x != 'tasks']
        if unknown:
            raise _types.InvalidScript(
                "Only tasks are currently supported for a script, got %s"
                % ', '.join(unknown))

        self.tasks = [engine._load_action(task) for task in tasks]

    def __call__(self, context: typing.Optional[Context] = None) -> typing.Any:
        """Execute the script."""
        if context is None:
            context = Context()

        for item in self.tasks:
            try:
                item(context)
            except _types.FinishScript as result:
                return result.result
            except _types.ExecutionFailed:
                raise
            except Exception as exc:
                raise _types.ExecutionFailed(
                    f"{exc.__class__.__name__} in {item.name}: {exc}")


_KNOWN_PARAMETERS = frozenset(['name', 'when', 'ignore_errors', 'register'])


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        actions: typing.Dict[str, typing.Type[_actions.Action]],
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

        self.actions = _BUILTINS.copy()
        self.actions.update(actions)
        self.logger = logging.getLogger(logger_name)
        self.environment = Environment()

    def execute(
        self,
        source: _types.SourceType,
        context: typing.Optional[Context] = None,
    ) -> typing.Any:
        """Execute a script.

        :param source: Script source code in JSON format.
        :param context: An application-specific context object.
        :return: The outcome of the script or `None`
        """
        Script(self, source)(context)

    def _load_action(
        self,
        definition: typing.Dict[str, typing.Any],
    ) -> _actions.Action:
        """Load an action from the definition.

        :param definition: JSON definition of an action.
        :return: An `Action`
        """
        matching = set(definition).intersection(self.actions)
        if not matching:
            raise _types.UnknownAction(
                "Action defined by one of %s is not known"
                % ','.join(definition))
        elif len(matching) > 1:
            raise _types.InvalidDefinition("Item with keys %s is ambiguous"
                                           % ','.join(matching))

        name = matching.pop()
        action = self.actions[name]
        params = definition[name]
        if not isinstance(params, (list, dict)):
            raise _types.InvalidDefinition(
                f"Parameters for action {name} must be a "
                f"list or an object, got {params}")
        elif isinstance(params, dict) and not all(isinstance(key, str)
                                                  for key in params):
            raise _types.InvalidDefinition(
                f"Parameters for action {name} must have string keys")

        # We have checked compliance above
        params = typing.cast(_types.ParamsType, params)

        top_level = {key: value for key, value in definition.items()
                     if key != name}
        when = top_level.pop('when', None)
        if when is not None:
            when = _actions.When(self, when)

        ignore_errors = top_level.pop('ignore_errors', False)
        if not isinstance(ignore_errors, bool):
            raise _types.InvalidDefinition(
                "The ignore_errors parameter must be a boolean for action "
                f"{name}, got {ignore_errors}")

        register = top_level.pop('register', None)
        if register is not None and not isinstance(register, str):
            raise _types.InvalidDefinition(
                "The register parameter must be a string "
                f"for action {name}, got {register}")

        display_name = top_level.pop('name', None)
        if display_name is not None and not isinstance(display_name, str):
            raise _types.InvalidDefinition(
                "The name parameter must be a string "
                f"for action {name}, got {display_name}")

        return action(self, params, display_name,
                      when, ignore_errors, register)

    def _evaluate(self, expr: str, context: Context) -> typing.Any:
        """Evaluate an expression."""
        return self.environment.from_string(expr, context).render()
