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
from miniscript import _task


class TestTask(miniscript.Task):
    required_params = {"object": None}
    optional_params = {"message": str, "number": int}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.side_effect = mock.Mock()

    def execute(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: miniscript.Context,
    ) -> typing.Optional[typing.Mapping[str, typing.Any]]:
        self.side_effect(object=params['object'])
        return {'result': params['object']}


class SingletonTask(miniscript.Task):
    required_params = {"message": str}
    singleton_param = "message"

    def execute(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        pass


class WrongSingletonTask(SingletonTask):
    singleton_param = "not_message"


class OptionalTask(miniscript.Task):
    optional_params = {"one": str, "two": int}
    allow_empty = False

    def execute(
        self,
        params: typing.MutableMapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        pass


class TaskLoadTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})

    def test_wrong_singleton(self):
        self.assertRaisesRegex(TypeError,
                               "singleton parameter",
                               WrongSingletonTask,
                               self.engine, {}, "wrong")

    def test_required(self):
        defn = {"test": {"object": {"answer": [42]}}}
        task = TestTask.load("test", defn, self.engine)
        self.assertEqual({"object": {"answer": [42]}}, task.params)

    def test_missing_required(self):
        defn = {"test": {"number": 42}}
        self.assertRaisesRegex(miniscript.InvalidDefinition,
                               "object are required",
                               TestTask.load,
                               "test", defn, self.engine)

    def test_wrong_params(self):
        for item in [42, True, object(), "banana!"]:
            defn = {"test": item}
            with self.subTest(params=item):
                self.assertRaisesRegex(miniscript.InvalidDefinition,
                                       f"accepts an object, not {item}",
                                       TestTask.load,
                                       "test", defn, self.engine)

    def test_wrong_keys(self):
        defn = {"test": {42: "answer"}}
        self.assertRaisesRegex(miniscript.InvalidDefinition,
                               "must have string keys",
                               TestTask.load,
                               "test", defn, self.engine)

    def test_wrong_top_level(self):
        for key in ["ignore_errors", "register", "name"]:
            defn = {"test": {}, key: 42}
            with self.subTest(top_level=key):
                self.assertRaisesRegex(miniscript.InvalidDefinition,
                                       f"{key}.*must be a",
                                       TestTask.load,
                                       "test", defn, self.engine)

    def test_optional_with_casting(self):
        defn = {"test": {"object": {"answer": [42]}, "number": "42"}}
        task = TestTask.load("test", defn, self.engine)
        self.assertEqual({"object": {"answer": [42]}, "number": 42},
                         task.params)

    def test_conditional(self):
        defn = {"test": {"object": {}}, "when": "1 == 1"}
        task = TestTask.load("test", defn, self.engine)
        self.assertEqual({"object": {}}, task.params)

    def test_singleton(self):
        defn = {"singleton": "test"}
        task = SingletonTask.load("singleton", defn, self.engine)
        self.assertEqual({"message": "test"}, task.params)

    def test_unknown(self):
        defn = {"test": {"object": {}, "who_am_I": None}}
        self.assertRaisesRegex(miniscript.InvalidDefinition,
                               "Parameter(s) who_am_I",
                               TestTask.load,
                               "test", defn, self.engine)

    def test_invalid_value(self):
        defn = {"test": {"object": {}, "number": "not number"}}
        self.assertRaisesRegex(miniscript.InvalidDefinition,
                               "Invalid value for parameter number",
                               TestTask.load,
                               "test", defn, self.engine)

    def test_one_required(self):
        defn = {"optional": None}
        self.assertRaisesRegex(miniscript.InvalidDefinition,
                               "At least one",
                               OptionalTask.load,
                               "optional", defn, self.engine)


class WhenTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})
        self.context = miniscript.Context(self.engine, answer=42)

    def test_one(self):
        when = _task.When(self.engine, "answer == 42")
        self.assertTrue(when(self.context))
        when = _task.When(self.engine, "answer is undefined")
        self.assertFalse(when(self.context))
        when = _task.When(self.engine, "{{ banana is undefined }}")
        self.assertTrue(when(self.context))

    def test_many_true(self):
        when = _task.When(self.engine, ["1 == 1", "answer == 42",
                                        "answer is defined"])
        self.assertTrue(when(self.context))
        when = _task.When(self.engine, ["1 == 1", "answer == 0",
                                        "answer is defined"])
        self.assertFalse(when(self.context))


class ExecuteTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})
        self.context = miniscript.Context(self.engine, answer=42)

    def test_normal(self):
        defn = {"test": {"object": "{{ answer }}"}}
        task = TestTask.load("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_called_once_with(object=42)

    def test_when_passed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer == 42"}
        task = TestTask.load("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_called_once_with(object=42)

    def test_when_not_passed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer is undefined or answer != 42"}
        task = TestTask.load("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_not_called()

    def test_when_failed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer.wrong.key == 42"}
        task = TestTask.load("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Failed to evaluate condition for test",
                               task, self.context)
        task.side_effect.assert_not_called()

    def test_execution_failed(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"}}
        task = TestTask.load("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Failed to execute task",
                               task, self.context)
        task.side_effect.assert_not_called()

    def test_ignore_errors(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"},
                "ignore_errors": True}
        task = TestTask.load("test", defn, self.engine)
        with mock.patch.object(self.engine.logger, 'warning',
                               autospec=True) as mock_log:
            self.assertIsNone(task(self.context))
            mock_log.assert_called_once()
        task.side_effect.assert_not_called()

    def test_register(self):
        defn = {"test": {"object": "{{ answer }}"}, "register": "varname"}
        task = TestTask.load("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        result = self.context['varname']
        self.assertIsInstance(result, miniscript.Result)
        self.assertEqual(42, result.result)
        self.assertTrue(result.succeeded)
        self.assertFalse(result.failed)
        self.assertIsNone(result.failure)

    def test_register_with_error(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"},
                "ignore_errors": True, "register": "varname"}
        task = TestTask.load("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        result = self.context['varname']
        self.assertIsInstance(result, miniscript.Result)
        self.assertFalse(result.succeeded)
        self.assertTrue(result.failed)
        self.assertIn("wrong", result.failure)
