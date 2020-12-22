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
import unittest
from unittest import mock

import miniscript
from miniscript import _types
from miniscript import tasks


class TestTask(miniscript.Task):
    required_params = {"object": None}
    optional_params = {"message": str, "number": int}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.side_effect = mock.Mock()

    def execute(
        self,
        params: typing.Mapping[str, typing.Any],
        context: miniscript.Context,
    ) -> typing.Optional[typing.Mapping[str, typing.Any]]:
        self.side_effect(object=params['object'])
        return {"result": params['object']}


class TasksTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({'test': TestTask})
        self.context = miniscript.Context(self.engine, answer=42)

    def test_return(self):
        defn = {"return": {"result": "{{ answer }}"}}
        task = tasks.Return("return", defn, self.engine)
        with self.assertRaises(_types.FinishScript) as exc_ctx:
            task(self.context)
        self.assertEqual(42, exc_ctx.exception.result)

    def test_return_singleton(self):
        defn = {"return": "{{ answer }}"}
        task = tasks.Return("return", defn, self.engine)
        with self.assertRaises(_types.FinishScript) as exc_ctx:
            task(self.context)
        self.assertEqual(42, exc_ctx.exception.result)

    def test_return_none(self):
        defn = {"return": None}
        task = tasks.Return("return", defn, self.engine)
        with self.assertRaises(_types.FinishScript) as exc_ctx:
            task(self.context)
        self.assertIsNone(exc_ctx.exception.result)

    def test_fail(self):
        defn = {"fail": {"msg": "I failed"}}
        task = tasks.Fail("fail", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Execution aborted: I failed",
                               task, self.context)

    def test_fail_singleton(self):
        defn = {"fail": "I failed"}
        task = tasks.Fail("fail", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Execution aborted: I failed",
                               task, self.context)

    def test_fail_msg_required(self):
        defn = {"fail": {}}
        task = tasks.Fail("fail", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "InvalidTask",
                               task, self.context)

    def test_block(self):
        defn = {"block": [
            {"test": {"object": "{{ answer + %d }}" % x}}
            for x in range(3)
        ]}
        task = tasks.Block("block", defn, self.engine)
        task(self.context)

    def test_log(self):
        for call in ("debug", "info", "warning", "error"):
            with self.subTest(call=call):
                defn = {"log": {call: "The answer was {{ answer }}"}}
                task = tasks.Log("log", defn, self.engine)
                with mock.patch.object(self.engine.logger, call,
                                       autospec=True) as mock_log:
                    task(self.context)
                    mock_log.assert_called_once_with("The answer was 42")

    def test_vars(self):
        defn = {"vars": {"next": "{{ answer + 1 }}", "cat": "orange"}}
        task = tasks.Vars("vars", defn, self.engine)
        task(self.context)
        self.assertEqual(43, self.context["next"])
        self.assertEqual("orange", self.context["cat"])
