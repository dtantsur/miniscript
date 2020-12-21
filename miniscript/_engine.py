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

from . import _context
from . import _task
from . import _types
from . import tasks


_BUILTINS: typing.Dict[str, typing.Type[_task.Task]] = {
    "block": tasks.Block,
    "fail": tasks.Fail,
    "log": tasks.Log,
    "return": tasks.Return,
    "vars": tasks.Vars,
}


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

    def __call__(
        self,
        context: typing.Optional[_context.Context] = None,
    ) -> typing.Any:
        """Execute the script."""
        if context is None:
            context = _context.Context(self.engine)

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


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        tasks: typing.Dict[str, typing.Type[_task.Task]],
        logger: typing.Optional[logging.Logger] = None,
    ) -> None:
        """Create a new engine.

        :param tasks: Mapping of tasks to their implementations.
        :param logger: Logger to use for all logging. If None, a default one
            is created.
        :raises: ValueError on conflicting tasks.
        """
        conflict = set(tasks).intersection(_task.Task._KNOWN_PARAMETERS)
        if conflict:
            raise ValueError('Tasks %s conflict with built-in parameters'
                             % ', '.join(conflict))

        self.tasks = _BUILTINS.copy()
        self.tasks.update(tasks)
        if logger is None:
            logger = logging.getLogger('miniscript')
        self.logger = logger
        self.environment = _context.Environment()

    def execute(
        self,
        source: _types.SourceType,
        context: typing.Optional[_context.Context] = None,
    ) -> typing.Any:
        """Execute a script.

        :param source: Script source code in JSON format.
        :param context: An application-specific context object.
        :return: The outcome of the script or `None`
        """
        return Script(self, source)(context)

    def _load_task(
        self,
        definition: typing.Dict[str, typing.Any],
    ) -> _task.Task:
        """Load a task from the definition.

        :param definition: JSON definition of a task.
        :return: An `Task`
        """
        matching = set(definition).intersection(self.tasks)
        if not matching:
            raise _types.UnknownTask(
                "Task defined by %s is not known" % ','.join(definition))
        elif len(matching) > 1:
            raise _types.InvalidDefinition("Item with keys %s is ambiguous"
                                           % ','.join(matching))

        name = matching.pop()
        task_class = self.tasks[name]
        return task_class.load(name, definition, self)
