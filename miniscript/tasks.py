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

"""Built-in task definitions."""

import typing

from . import _task
from . import _types

if typing.TYPE_CHECKING:
    from . import _context


class Block(_task.Task):
    """Grouping of tasks."""

    required_params = {"tasks": list}

    singleton_param = "tasks"

    def validate(
        self,
        params: _types.ParamsType
    ) -> typing.Dict[str, typing.Any]:
        tasks = super().validate(params)["tasks"]
        tasks = [self.engine._load_task(task) for task in tasks]
        return {"tasks": tasks}

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_context.Context',
    ) -> None:
        for task in params["tasks"]:
            task(context)


class Fail(_task.Task):
    """Fail the execution."""

    required_params = {'msg': str}

    singleton_param = 'msg'

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_context.Context',
    ) -> None:
        raise _types.ExecutionFailed(f"{self.name} aborted: {params['msg']}")


class Log(_task.Task):
    """Log something."""

    optional_params = {
        key: str for key in ("debug", "info", "warning", "error")}

    allow_empty = False

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_context.Context'
    ) -> None:
        for key, value in params.items():
            getattr(self.engine.logger, key)(value)


class Return(_task.Task):
    """Return a value to the caller."""

    optional_params = {'result': None}

    singleton_param = 'result'

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_context.Context',
    ) -> None:
        raise _types.FinishScript(params.get('result'))


class Vars(_task.Task):
    """Set some variables."""

    free_form = True

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: '_context.Context'
    ) -> None:
        for key, value in params.items():
            context[key] = value
