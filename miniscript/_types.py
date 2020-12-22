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

import typing


SourceType = typing.Union[
    typing.List[typing.Dict[str, typing.Any]],
    typing.Dict[str, typing.Any]
]
"""Type of a script source."""


JsonType = typing.Union[
    typing.Dict[str, typing.Any],
    typing.List,
    str,
    int,
    bool,
    None
]


ParamsType = typing.Union[
    typing.Dict[str, JsonType],
    typing.List[JsonType],
    None
]


class Error(Exception):
    """Base class for all errors."""


class ExecutionFailed(Error, RuntimeError):
    """Execution of a task failed."""


class InvalidScript(Error, TypeError):
    """The script definition is invalid."""


class InvalidDefinition(Error, ValueError):
    """A definition of a task is invalid."""


class UnknownTask(InvalidDefinition):
    """An task is not known."""


class FinishScript(BaseException):
    """Finish the script successfully."""

    def __init__(self, result: typing.Any):
        self.result = result


class Aborted(ExecutionFailed):
    """Abort the script."""
