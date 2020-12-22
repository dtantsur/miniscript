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


class Script:
    """A script.

    :param engine: An :class:`Engine`.
    :param source: A source definition or a list of tasks to execute.
    """

    engine: 'Engine'
    """The :class:`Engine` of this script."""

    tasks: typing.List[_task.Task]
    """A list of :class:`Tasks` in the order of execution."""

    def __init__(
        self,
        engine: 'Engine',
        source: typing.Union[
            typing.List[typing.Dict[str, typing.Any]],
            typing.Dict[str, typing.Any]
        ],
    ) -> None:
        """Create a new script."""
        if isinstance(source, list):
            source = {'tasks': source}

        self.engine = engine

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
        """Execute the script.

        :param context: A :class:`Context` object to hold execution context.
        :return: The outcome of the script or `None`
        :raises: :class:`ExecutionFailed` on a runtime error.
        :raises: :class:`InvalidScript` if the script is invalid.
        :raises: :class:`InvalidTask` if a task is invalid.
        """
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
                msg = (f"Failed to execute task {item.name}. "
                       f"{exc.__class__.__name__}: {exc}")
                self.engine.logger.error("Execution failed: %s", msg)
                raise _types.ExecutionFailed(msg)


# Fix Engine documentation when updating this.
_BUILTINS: typing.Dict[str, typing.Type[_task.Task]] = {
    "block": tasks.Block,
    "fail": tasks.Fail,
    "log": tasks.Log,
    "return": tasks.Return,
    "vars": tasks.Vars,
}


class Engine:
    """Engine that runs scripts.

    :param tasks: Tasks to use for this engine, see :attr:`Engine.tasks`.
    :param logger: Logger to use for all logging. If `None`, a default one
        is created.
    :raises: ValueError on tasks conflicting with built-in parameters, see
        :class:`Task`.

    The development flow is:

    #. define your tasks by subclassing :class:`Task`;
    #. create an :class:`Engine` with the task definitions;
    #. (optionally) create a custom :class:`Context`;
    #. run :meth:`Engine.execute`.

    Preparing an engine:

    .. code-block:: python

        import miniscript

        class AddTask(miniscript.Task):
            required_params = {'values': list}
            singleton_param = 'values'

            def validate(self, params, context):
                for item in params['values']:
                    int(item)

            def execute(self, params, context):
                return {"sum": sum(params['values'])}

        engine = miniscript.Engine({'add': AddTask})

    Some tasks are built into the engine:

    * ``block`` - :class:`tasks.Block`
    * ``fail`` - :class:`tasks.Fail`
    * ``log`` - :class:`tasks.Log`
    * ``return`` - :class:`tasks.Return`
    * ``vars`` - :class:`tasks.Vars`

    An example script:

    .. code-block:: yaml

        ---
        - name: add some values
          add:
            - 23423
            - 43874
            - 22834
          register: result

        - name: log the result
          log:
            info: "The sum is {{ result.sum }}"

        - name: return the result
          return: "{{ result.sum }}"

    Executing a script (obviously, it does not have to come from YAML):

    .. code-block:: python

        import yaml

        with open("script.yaml") as fp:
            code = yaml.safe_load(fp)

        result = engine.execute(code)  # result == 90131
    """

    tasks: typing.Dict[str, typing.Type[_task.Task]]
    """Mapping of task names to their implementation classes.

    The name will be used in a script. The implementation must be
    a :class:`Task` subclass (not an instance).

    Includes built-in tasks.
    """

    logger: logging.Logger
    """Python logger used for logging."""

    environment: _context.Environment
    """An :class:`Environment` object used for templating."""

    def __init__(
        self,
        tasks: typing.Dict[str, typing.Type[_task.Task]],
        logger: typing.Optional[logging.Logger] = None,
    ) -> None:
        """Create a new engine."""
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
        source: typing.Union[
            typing.List[typing.Dict[str, typing.Any]],
            typing.Dict[str, typing.Any]
        ],
        context: typing.Optional[_context.Context] = None,
    ) -> typing.Any:
        """Execute a script.

        :param source: Script source code in JSON format.
            An implicit :class:`Script` object is created from it.
        :param context: A :class:`Context` object to hold execution context.
        :return: The outcome of the script or `None`
        :raises: :class:`ExecutionFailed` on a runtime error.
        :raises: :class:`InvalidScript` if the script is invalid.
        :raises: :class:`InvalidTask` if a task is invalid.
        """
        return Script(self, source)(context)

    def _load_task(
        self,
        definition: typing.Dict[str, typing.Any],
    ) -> _task.Task:
        """Load a task from the definition.

        :param definition: JSON definition of a task.
        :return: A :class:`Task`.
        """
        matching = set(definition).intersection(self.tasks)
        if not matching:
            raise _types.UnknownTask(
                "Task defined by %s is not known" % ', '.join(definition))
        elif len(matching) > 1:
            raise _types.InvalidTask("Item with keys %s is ambiguous"
                                     % ','.join(matching))

        name = matching.pop()
        task_class = self.tasks[name]
        return task_class(name, definition, self)
