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

from . import _tasks
from . import _types


class Environment(sandbox.Environment):  # type: ignore
    """A templating environment."""

    code_generator_class = nativetypes.NativeCodeGenerator
    template_class = nativetypes.NativeTemplate


_BUILTINS: typing.Dict[str, typing.Type[_tasks.Task]] = {
    "block": _tasks.Block,
    "fail": _tasks.Fail,
    "log": _tasks.Log,
    "return": _tasks.Return,
    "vars": _tasks.Vars,
}


class Context(dict):
    """A context of an execution."""

    __slots__ = ()


class Script:
    """A prepared script."""

    def __init__(self, engine: 'Engine', source: _types.SourceType) -> None:
        """Create a new script.

        :param engine: An `Engine`.
        :param source: A source definition or a list of tasks to execute.
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

        self.tasks = [engine._load_task(task) for task in tasks]

    def __call__(self, context: typing.Optional[Context] = None) -> typing.Any:
        """Execute the script."""
        if context is None:
            context = Context()

        for item in self.tasks:
            self.engine.logger.debug("Execution task %s", item.name)
            try:
                item(context)
            except _types.FinishScript as result:
                self.engine.logger.info("Execution finished with result %s",
                                        result.result)
                return result.result
            except _types.ExecutionFailed as exc:
                self.engine.logger.error("Execution failed: %s", exc)
                raise
            except Exception as exc:
                msg = f"{exc.__class__.__name__} in {item.name}: {exc}"
                self.engine.logger.error("Execution failed: %s", msg)
                raise _types.ExecutionFailed(msg)


_KNOWN_PARAMETERS = frozenset(['name', 'when', 'ignore_errors', 'register'])


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        tasks: typing.Dict[str, typing.Type[_tasks.Task]],
        logger: typing.Optional[logging.Logger] = None,
    ) -> None:
        """Create a new engine.

        :param tasks: Mapping of tasks to their implementations.
        :param logger: Logger to use for all logging. If None, a default one
            is created.
        :raises: ValueError on conflicting tasks.
        """
        conflict = set(tasks).intersection(_KNOWN_PARAMETERS)
        if conflict:
            raise ValueError('Tasks %s conflict with built-in parameters'
                             % ', '.join(conflict))

        self.tasks = _BUILTINS.copy()
        self.tasks.update(tasks)
        if logger is None:
            logger = logging.getLogger('miniscript')
        self.logger = logger
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

    def _load_task(
        self,
        definition: typing.Dict[str, typing.Any],
    ) -> _tasks.Task:
        """Load a task from the definition.

        :param definition: JSON definition of a task.
        :return: An `Task`
        """
        matching = set(definition).intersection(self.tasks)
        if not matching:
            raise _types.UnknownTask(
                "Task defined by one of %s is not known"
                % ','.join(definition))
        elif len(matching) > 1:
            raise _types.InvalidDefinition("Item with keys %s is ambiguous"
                                           % ','.join(matching))

        name = matching.pop()
        task_class = self.tasks[name]
        params = definition[name]
        if not isinstance(params, (list, dict)):
            raise _types.InvalidDefinition(
                f"Parameters for task {name} must be a "
                f"list or an object, got {params}")
        elif isinstance(params, dict) and not all(isinstance(key, str)
                                                  for key in params):
            raise _types.InvalidDefinition(
                f"Parameters for task {name} must have string keys")

        # We have checked compliance above
        params = typing.cast(_types.ParamsType, params)

        top_level = {key: value for key, value in definition.items()
                     if key != name}
        when = top_level.pop('when', None)
        if when is not None:
            when = _tasks.When(self, when)

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

        return task_class(self, params, display_name or name,
                          when, ignore_errors, register)

    def _evaluate(self, expr: str, context: Context) -> typing.Any:
        """Evaluate an expression."""
        return self.environment.from_string(expr, context).render()
