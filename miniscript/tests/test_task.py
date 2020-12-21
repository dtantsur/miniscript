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

import miniscript
from miniscript import _task


class TestTask(miniscript.Task):
    required_params = {"object": None}
    optional_params = {"message": str, "number": int}

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: miniscript.Context,
    ) -> typing.Any:
        pass


class SingletonTask(miniscript.Task):
    required_params = {"message": str}
    singleton_param = "message"

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: miniscript.Context,
    ) -> typing.Any:
        pass


class WrongSingletonTask(SingletonTask):
    singleton_param = "not_message"


class OptionalTask(miniscript.Task):
    optional_params = {"one": str, "two": int}
    allow_empty = False

    def execute(
        self,
        params: typing.Dict[str, typing.Any],
        context: miniscript.Context,
    ) -> typing.Any:
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
