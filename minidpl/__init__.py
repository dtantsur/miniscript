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


DictType = typing.Dict[str, typing.Any]


JsonType = typing.Union[
    DictType,
    typing.List,
    str,
    int,
    bool,
    None
]


class Error(Exception):
    """Base class for all errors."""


class InvalidDefinition(Error, ValueError):
    """A definition of an action or condition is invalid."""


class UnknownItem(InvalidDefinition):
    """A condition or action is not known."""


class Item(metaclass=abc.ABCMeta):
    """An abstract base class for an item."""

    def process_params(
        self,
        top_level: JsonType,
        internal: JsonType,
        engine: 'Engine',
    ) -> DictType:
        """Process collected parameters.

        The base version only allows dictionaries and pass them unprocessed.

        :param top_level: Incoming parameters defined at the top level.
        :param internal: Incoming parameters defined under the item key.
        :param engine: An `Engine`.
        :return: Processed parameters as a dictionary.
        """
        if not isinstance(top_level, dict):
            raise TypeError("%s: expected a %s, got %s"
                            % (self.__class__.__name__,
                               DictType,
                               type(top_level).__name__))
        if not isinstance(internal, dict):
            raise TypeError("%s: expected a %s, got %s"
                            % (self.__class__.__name__,
                               DictType,
                               type(internal).__name__))
        return dict(top_level, **internal)


class Condition(Item):
    """An abstract base class for a condition."""

    @abc.abstractmethod
    def check(self, params: DictType, context: typing.Any) -> bool:
        """Check that the condition fullfils.

        :param params: Parameters processed via `process_params`.
        :param context: An application-specific object passed to Engine.
        :return: Whether the condition fullfils.
        """


class Action(Item):
    """An abstract base class for an action."""

    @abc.abstractmethod
    def execute(self, params: DictType, context: typing.Any) -> None:
        """Execute the action.

        :param params: Parameters processed via `process_params`.
        :param context: An application-specific object passed to Engine.
        """


class Executable:
    """An action prepared for execution."""

    def __init__(self, action: Action, params: DictType) -> None:
        """Create a prepared action."""
        self.action = action
        self.params = params

    def execute(self, context: typing.Any) -> None:
        """Execute the action.

        :param context: An application-specific object passed to Engine.
        """
        self.action.execute(self.params, context)


class Script:
    """A prepared script."""

    def __init__(
        self,
        engine: 'Engine',
        source: typing.List[Executable],
    ) -> None:
        """Create a new script.

        :param engine: An `Engine`.
        :param source: A list of actions to execute.
        """
        self.engine = engine
        self.source = source

    def execute(self, context: typing.Any) -> None:
        """Execute the script."""
        for item in self.source:
            item.execute(context)


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        actions: typing.Dict[str, Action],
        conditions: typing.Dict[str, Condition] = None,
        negation: str = '~',
        enable_builtins: bool = True,
    ) -> None:
        """Create a new engine.

        :param conditions: Mapping of conditions to their implementations.
        :param actions: Mapping of actions to their implementations.
        :param negation: A string used to negate conditions.
        """
        self.actions = actions
        self.conditions = conditions or {}
        self.negation = negation

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
        self.prepare(source).execute(context)

    def load_action(self, definition: DictType) -> Executable:
        """Load an action from the definition.

        :param definition: JSON definition of an action.
        :return: An `Executable`
        """
        matching = set(definition).intersection(self.actions)
        if not matching:
            raise UnknownItem("Item defined by one of %s is not known"
                              % ','.join(definition))
        elif len(matching) > 1:
            raise InvalidDefinition("Item with keys %s is ambiguous"
                                    % ','.join(matching))

        name = matching.pop()
        action = self.actions[name]

        top_level = {key: value for key, value in definition.items()
                     if key != name}
        internal = definition[name]

        params = self.process_params(action, top_level, internal)
        return Executable(action, params)

    def prepare(
        self,
        source: typing.Union[typing.List[DictType], DictType],
    ) -> Script:
        """Prepare a script for execution.

        :param source: Script source code in JSON format.
        :return: A `Script` object for execution.
        """
        if isinstance(source, dict):
            source = [source]

        parsed = [self.load_action(item) for item in source]
        return Script(self, parsed)

    def process_params(
        self,
        item: Item,
        top_level: JsonType,
        internal: JsonType,
    ) -> DictType:
        """Process collected parameters.

        The base version only allows dictionaries and pass them unprocessed.

        :param item: An action or a condition.
        :param top_level: Incoming parameters defined at the top level.
        :param internal: Incoming parameters defined under the item key.
        :return: Processed parameters as a dictionary.
        """
        return item.process_params(top_level, internal, self)
