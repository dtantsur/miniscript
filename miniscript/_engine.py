import logging
import typing

import jinja2

from . import _context
from . import _task
from . import _types
from . import filters
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
                try:
                    item(context)
                except _types.FinishScript as result:
                    value = _context.materialize(result.result)
                    if isinstance(value, jinja2.Undefined):
                        raise _types.ExecutionFailed(
                            "Script returned undefined value") from None
                    self.engine.logger.info(
                        "Execution finished with result %s", value)
                    return value
            except _types.ExecutionFailed as exc:
                self.engine.logger.error("Execution failed: %s", exc)
                raise
            except Exception as exc:
                msg = (f"Failed to execute task {item.name}. "
                       f"{exc.__class__.__name__}: {exc}")
                self.engine.logger.error("Execution failed: %s", msg)
                raise _types.ExecutionFailed(msg)


_BUILTINS: typing.Dict[str, typing.Type[_task.Task]] = {
    name.lower(): getattr(tasks, name) for name in tasks.__all__
}

_FILTERS: typing.Dict[str, typing.Callable] = {
    name.rstrip('_'): getattr(filters, name) for name in filters.__all__
}


class Engine:
    """Engine that runs scripts.

    :param tasks: Tasks to use for this engine, see :attr:`Engine.tasks`.

        .. versionchanged:: 1.1
           Tasks are now optional, only built-in tasks are used by default.
    :param logger: Logger to use for all logging. If `None`, a default one
        is created.
    :param additional_filters: If `True`, additional Ansible-compatible filters
        from :mod:`miniscript.filters` are enabled.

        .. versionadded:: 1.1
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
            '''A task implementing addition.'''

            required_params = {'values': list}
            '''One required parameter - a list of values.'''
            singleton_param = 'values'
            '''Can be supplied without an explicit "values".'''

            def validate(self, params, context):
                '''Validate the parameters.'''
                super().validate(params, context)
                for item in params['values']:
                    int(item)

            def execute(self, params, context):
                '''Execute the action, return a "sum" value.'''
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
        - name: only accept positive integers
          fail: "{{ item }} must be positive"
          when: item <= 0
          loop: "{{ values }}"

        - name: add the provided values
          add: "{{ values }}"
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

        # The context holds all variables.
        context = miniscript.Context(engine, values=[23423, 43874, 22834])

        # Unlike Ansible, MiniScript can return a result!
        result = engine.execute(code, context)  # result == 90131
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
        tasks: typing.Optional[
            typing.Dict[str, typing.Type[_task.Task]]
        ] = None,
        logger: typing.Optional[logging.Logger] = None,
        additional_filters: bool = True,
    ) -> None:
        """Create a new engine."""
        self.tasks = _BUILTINS.copy()
        if tasks is not None:
            conflict = set(tasks).intersection(_task.Task._KNOWN_PARAMETERS)
            if conflict:
                raise ValueError(f"Tasks {', '.join(conflict)} conflict with "
                                 "built-in parameters")
            self.tasks.update(tasks)

        if logger is None:
            logger = logging.getLogger('miniscript')
        self.logger = logger
        self.environment = _context.Environment()
        if additional_filters:
            self.environment.filters.update(_FILTERS)

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
        :return: The outcome of the script or `None`.

            .. note:: :class:`ExecutionFailed` is raised if a script returns
                      an undefined value.
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
