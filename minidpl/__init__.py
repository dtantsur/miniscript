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
    typing.List[typing.Any],
    str,
    int,
    bool,
    None
]


class Item(metaclass=abc.ABCMeta):
    """An abstract base class for an item."""

    def process_params(self, params: JsonType) -> typing.Dict[str, typing.Any]:
        """Process collected parameters.

        The base version only allows dictionaries and pass them unprocessed.
        """
        if isinstance(params, dict):
            return params
        else:
            raise TypeError("%s: expected a %s, got %s"
                            % (self.__class__.__name__,
                               DictType,
                               type(params).__name__))


class Condition(Item):
    """An abstract base class for a condition."""


class Action(Item):
    """An abstract base class for an action."""


class Engine:
    """Data processing engine."""

    def __init__(
        self,
        conditions: typing.Dict[str, Condition],
        actions: typing.Dict[str, Action],
        negation: str = '~',
        enable_builtins: bool = True,
    ) -> None:
        """Create a new engine.

        :param conditions: Mapping of conditions to their implementations.
        :param actions: Mapping of actions to their implementations.
        :param negation: A string used to negate conditions.
        """
        self.conditions = conditions
        self.actions = actions
        self.negation = negation
