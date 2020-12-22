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


JsonType = typing.Union[
    typing.Dict[str, typing.Any],
    typing.List,
    str,
    int,
    bool,
    None
]


class Error(Exception):
    """Base class for all errors."""


class ExecutionFailed(Error):
    """Execution of a task failed."""


class InvalidScript(Error):
    """The script definition is invalid."""


class InvalidTask(Error):
    """The task definition is invalid."""


class UnknownTask(InvalidTask):
    """An task is not known."""


class FinishScript(BaseException):
    """Finish the script successfully."""

    def __init__(self, result: typing.Any):
        self.result = result


class Aborted(ExecutionFailed):
    """Abort the script."""
