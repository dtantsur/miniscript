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
    """A result of a task.

    Any resulting values are stored directly on the object.
    """

    succeeded: bool
    """Whether the task succeeded (the opposite of :attr:`Result.failed`)."""

    failed: bool
    """Whether the task failed (the opposite of :attr:`Result.succeeded`)."""

    failure: typing.Optional[str] = None
    """Failure message if the task failed."""

    skipped: bool = False
    """Whether the task was skipped via a `when` statement."""

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
    """An abstract base class for a task.

    An implementation must override :meth:`Task.execute` and may also override
    :meth:`Task.validate`, although it is usually not necessary.

    :param name: Name of this task as used in the script.
    :param definition: The task definition from the script.
    :param engine: An :class:`Engine` the task is executed on.
    """

    required_params: typing.Dict[str, typing.Optional[typing.Type]] = {}
    """A mapping with required parameters.

    A value is either `None` or one of the supported types:
    `str`, `int`, `float`, `list`.
    """

    optional_params: typing.Dict[str, typing.Optional[typing.Type]] = {}
    """A mapping with optional parameters.

    See :attr:`Task.required_params` for a list of supported types.
    """

    singleton_param: typing.Optional[str] = None
    """A name for the parameter to store if the input is not an object.

    For example (see :class:`tasks.Fail`),

    .. code-block:: yaml

        - fail: I have failed

    is converted to

    .. code-block:: yaml

        - fail:
            msg: I have failed
    """

    free_form: bool = False
    """Whether this task accepts any arguments.

    Validation for known arguments is still run, and required parameters are
    still required.
    """

    allow_empty: bool = True
    """If no parameters are required, whether to allow empty input.

    Makes no sense if :attr:`Task.required_params` is not empty.
    """

    _KNOWN_PARAMETERS = frozenset(
        ['name', 'when', 'ignore_errors', 'register', 'loop'])

    # Keep up-to-date with the documentation above.
    _VALID_TYPES = (str, int, float, list)

    engine: '_engine.Engine'
    """The :class:`Engine` this task uses."""

    name: str
    """The description of this task in the script.

    If a human-readable description is not provided, uses the task name.
    """

    when: typing.Optional[typing.Callable[[_context.Context], bool]] = None
    """A condition of this task.

    Specified via the ``when`` statement and supports templating, e.g.:

    .. code-block:: yaml

        - fail: Address must be defined
          when: address is undefined
    """

    ignore_errors: bool = False
    """Whether to ignore errors and continue execution.

    Often used together with :attr:`Task.register` as

    .. code-block:: yaml

        - name: run a task that can fail
          task_that_can_fail:
          ignore_errors: True
          register: fallible_result

        - name: log if the task failed
          log:
            warning: "Task failed: {{ fallible_result.failure }}"
          when: fallible_result.failed
    """

    register: typing.Optional[str] = None
    """Variable to store the result of this task as a :class:`Result`."""

    loop: typing.Union[str, list, None] = None
    """Value to loop over.

    For each item in the resulting list, execute the task passing the item
    as the ``item`` value in the context.

    .. code-block:: yaml

        - name: do excessive logging
          log:
            info: "I like number {{ item }}"
          loop: [1, 2, 3, 4, 5]

    Conditions are evaluated separately for each item:

    .. code-block:: yaml

        - name: do excessive logging
          log:
            info: "I like even numbers like {{ item }}"
          loop: [1, 2, 3, 4, 5]
          when: item % 2 == 0

    The loop value itself may be a template yielding a list.
    """

    params: typing.Mapping[str, typing.Any]
    """Task parameter after passing preliminary validation.

    Evaluating templated variables is not possible until execution, so this
    field may contain raw templates.
    """

    def __init__(
        self,
        name: str,
        definition: typing.Dict[str, typing.Any],
        engine: '_engine.Engine',
    ):
        """Load a task from its definition.

        This call can be overridden to provide more parameters common for
        all tasks.
        """
        self.engine = engine

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

        params = definition[name]
        top_level = {key: value for key, value in definition.items()
                     if key != name}

        when = top_level.pop('when', None)
        if when is not None:
            self.when = When(engine, when)

        self.ignore_errors = top_level.pop('ignore_errors', False)
        if not isinstance(self.ignore_errors, bool):
            raise _types.InvalidTask(
                "The ignore_errors parameter must be a boolean for task "
                f"{name}, got {self.ignore_errors}")

        self.register = top_level.pop('register', None)
        if self.register is not None and not isinstance(self.register, str):
            raise _types.InvalidTask(
                "The register parameter must be a string "
                f"for task {name}, got {self.register}")

        self.name = top_level.pop('name', name)
        if not isinstance(self.name, str):
            raise _types.InvalidTask(
                "The name parameter must be a string "
                f"for task {name}, got {self.name}")

        self.loop = top_level.pop('loop', None)
        if self.loop is not None and not isinstance(self.loop, (str, list)):
            raise _types.InvalidTask(
                "The loop parameter must be a template or a list "
                f"for task {name}, got {self.loop}")

        if top_level:
            raise _types.InvalidTask(
                f"Unknown top-level parameters {', '.join(top_level)} "
                f"for task {name}")

        if params is None:
            params = {}
        elif (isinstance(params, abcoll.Mapping)
              and not all(isinstance(key, str) for key in params)):
            raise _types.InvalidTask(
                f"Parameters for task {self.name} must have string keys")
        elif not isinstance(params, abcoll.Mapping):
            if self.singleton_param is None:
                raise _types.InvalidTask(
                    f"Task {self.name} accepts an object, not {params}")
            params = {self.singleton_param: params}
        self.params = params

    def validate(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: _context.Context,
    ) -> None:
        """Validate the passed parameters.

        The call may modify the parameters in-place, e.g. to apply type
        conversion. The default implementation relies on class-level
        :attr:`Task.required_params`, :attr:`Task.optional_params`,
        :attr:`Task.singleton_param`, :attr:`Task.free_form` and
        :attr:`Task.allow_empty` for parameter validation.

        :param params: The current parameters as a mapping that automatically
            evaluates templates on access.
        :param context: A :class:`Context` object to hold execution context.
        """
        known = dict(self.required_params, **self.optional_params)

        unknown = set(params).difference(known)
        if not self.free_form and unknown:
            raise _types.InvalidTask(
                "parameter(s) not recognized: %s"
                % ', '.join("'%s'" % item for item in unknown))

        missing = set(self.required_params).difference(params)
        if missing:
            raise _types.InvalidTask(
                "parameter(s) required: %s"
                % ', '.join("'%s'" % item for item in missing))

        if not params and not self.allow_empty:
            raise _types.InvalidTask(
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
                raise _types.InvalidTask(
                    f"invalid value for parameter '{name}': {exc}")

    def __call__(self, context: _context.Context) -> None:
        """Check conditions and execute the task in the context.

        It is not recommended to override this method, see :meth:`Task.execute`
        instead.

        :param context: A :class:`Context` object to hold execution context.
        """
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
        params: typing.Mapping[str, typing.Any],
        context: _context.Context,
    ) -> typing.Optional[typing.Mapping[str, typing.Any]]:
        """Execute the task.

        Override this method to provide the task logic.

        :param params: Validated parameters as a mapping that automatically
            evaluates templates.
        :param context: A :class:`Context` object to hold execution context.
            It is a mutable mapping that holds variables.
        :returns: Values stored in a :class:`Result` if :attr:`Task.register``
            is set (otherwise discarded). A mapping from names to values.
        """
