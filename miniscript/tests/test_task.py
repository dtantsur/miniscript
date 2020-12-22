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
from miniscript import _context
from miniscript import _task


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
        return {'result': params['object']}


class SingletonTask(miniscript.Task):
    required_params = {"message": str}
    singleton_param = "message"

    def execute(
        self,
        params: typing.Mapping[str, typing.Any],
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
        params: typing.Mapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        pass


class WrongTypesTask(TestTask):
    optional_params = {"message": dict}


class TaskLoadTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})

    def test_wrong_singleton(self):
        self.assertRaisesRegex(TypeError,
                               "singleton parameter",
                               WrongSingletonTask,
                               self.engine, {}, "wrong")

    def test_wrong_type(self):
        self.assertRaisesRegex(TypeError,
                               "Acceptable types",
                               WrongTypesTask,
                               self.engine, {}, "wrong")

    def test_ok(self):
        defn = {"test": {"object": {"answer": [42]}}}
        task = TestTask("test", defn, self.engine)
        self.assertEqual({"object": {"answer": [42]}}, task.params)

    def test_wrong_params(self):
        for item in [42, True, object(), "banana!"]:
            defn = {"test": item}
            with self.subTest(params=item):
                self.assertRaisesRegex(miniscript.InvalidTask,
                                       f"accepts an object, not {item}",
                                       TestTask,
                                       "test", defn, self.engine)

    def test_wrong_keys(self):
        defn = {"test": {42: "answer"}}
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "must have string keys",
                               TestTask,
                               "test", defn, self.engine)

    def test_unexpected_top_level(self):
        defn = {"test": {}, "key": 42}
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "Unknown top-level.*key",
                               TestTask,
                               "test", defn, self.engine)

    def test_wrong_top_level(self):
        for key in ["ignore_errors", "register", "name", "loop"]:
            defn = {"test": {}, key: 42}
            with self.subTest(top_level=key):
                self.assertRaisesRegex(miniscript.InvalidTask,
                                       f"{key}.*must be a",
                                       TestTask,
                                       "test", defn, self.engine)

    def test_conditional(self):
        defn = {"test": {"object": {}}, "when": "1 == 1"}
        task = TestTask("test", defn, self.engine)
        self.assertEqual({"object": {}}, task.params)

    def test_singleton(self):
        defn = {"singleton": "test"}
        task = SingletonTask("singleton", defn, self.engine)
        self.assertEqual({"message": "test"}, task.params)


class TaskValidateTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})
        self.context = miniscript.Context(self.engine, answer=42)

    def test_validate(self):
        defn = {"test": {"object": {"answer": [42]}, "number": "42"}}
        task = TestTask("test", defn, self.engine)
        self.assertEqual({"object": {"answer": [42]}, "number": "42"},
                         task.params)
        task.validate(task.params, self.context)
        # "42" -> 42
        self.assertEqual({"object": {"answer": [42]}, "number": 42},
                         task.params)

    def test_missing_required(self):
        defn = {"test": {"number": 42}}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "required: 'object'",
                               task.validate, task.params, self.context)

    def test_unknown(self):
        defn = {"test": {"object": {}, "who_am_I": None}}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "not recognized: 'who_am_I'",
                               task.validate, task.params, self.context)

    def test_invalid_value(self):
        defn = {"test": {"object": {}, "number": "not number"}}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "invalid value for parameter 'number'",
                               task.validate, task.params, self.context)

    def test_one_required(self):
        defn = {"optional": None}
        task = OptionalTask("optional", defn, self.engine)
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "at least one",
                               task.validate, task.params, self.context)

    def test_eager_validation(self):
        defn = {"test": {"object": {}, "number": "{{ not_found }}"}}
        task = TestTask("test", defn, self.engine)
        params = _context.Namespace(
            self.engine.environment, self.context, task.params)
        # Since "number" has a type constrained, it has to be evaluated.
        self.assertRaisesRegex(miniscript.InvalidTask,
                               "'not_found' is undefined",
                               task.validate, params, self.context)

    def test_lazy_validation(self):
        defn = {"test": {"object": "{{ not_found }}"}}
        task = TestTask("test", defn, self.engine)
        params = _context.Namespace(
            self.engine.environment, self.context, task.params)
        # Since "object" is not constrained, it's not evaluated now.
        task.validate(params, self.context)


class WhenTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})
        self.context = miniscript.Context(self.engine, answer=42,
                                          result=miniscript.Result({}))

    def test_one(self):
        when = _task.When(self.engine, "answer == 42")
        self.assertTrue(when(self.context))
        when = _task.When(self.engine, "answer is undefined")
        self.assertFalse(when(self.context))
        when = _task.When(self.engine, "{{ banana is undefined }}")
        self.assertTrue(when(self.context))
        when = _task.When(self.engine, "not result.succeeded")
        self.assertFalse(when(self.context))

    def test_many_true(self):
        when = _task.When(self.engine, ["1 == 1", "answer == 42",
                                        "result.succeeded",
                                        "not result.skipped",
                                        "answer is defined"])
        self.assertTrue(when(self.context))
        when = _task.When(self.engine, ["1 == 1", "answer == 0",
                                        "answer is defined"])
        self.assertFalse(when(self.context))


class ExecuteTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({})
        self.context = miniscript.Context(
            self.engine, answer=42, items=["{{ answer }}", 43, 44])

    def test_normal(self):
        defn = {"test": {"object": "{{ answer }}"}}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_called_once_with(object=42)

    def test_when_passed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer == 42"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_called_once_with(object=42)

    def test_when_not_passed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer is undefined or answer != 42"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_not_called()

    def test_when_failed(self):
        defn = {"test": {"object": "{{ answer }}"},
                "when": "answer.wrong.key == 42"}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Failed to evaluate condition for test",
                               task, self.context)
        task.side_effect.assert_not_called()

    def test_execution_failed(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"}}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Failed to execute task",
                               task, self.context)
        task.side_effect.assert_not_called()

    @mock.patch.object(TestTask, 'execute', autospec=True, return_value=42)
    def test_execution_wrong_result(self, mock_execute):
        defn = {"test": {"object": "{{ answer }}"}}
        task = TestTask("test", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "must return None or a mapping",
                               task, self.context)
        mock_execute.assert_called_once_with(task, mock.ANY, self.context)

    def test_ignore_errors(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"},
                "ignore_errors": True}
        task = TestTask("test", defn, self.engine)
        with mock.patch.object(self.engine.logger, 'warning',
                               autospec=True) as mock_log:
            self.assertIsNone(task(self.context))
            mock_log.assert_called_once()
        task.side_effect.assert_not_called()

    def test_register(self):
        defn = {"test": {"object": "{{ answer }}"}, "register": "varname"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        result = self.context['varname']
        self.assertIsInstance(result, miniscript.Result)
        self.assertEqual(42, result.result)
        self.assertTrue(result.succeeded)
        self.assertFalse(result.failed)
        self.assertIsNone(result.failure)
        self.assertFalse(result.skipped)

    def test_register_with_error(self):
        defn = {"test": {"object": "{{ answer.wrong.key }}"},
                "ignore_errors": True, "register": "varname"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        result = self.context['varname']
        self.assertIsInstance(result, miniscript.Result)
        self.assertFalse(result.succeeded)
        self.assertTrue(result.failed)
        self.assertIn("wrong", result.failure)
        self.assertFalse(result.skipped)

    def test_loop_simple(self):
        defn = {"test": {"object": "{{ item }}"}, "loop": [1, 2, None]}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_has_calls([
            mock.call(object=x) for x in [1, 2, None]
        ])

    def test_loop_variable(self):
        defn = {"test": {"object": "{{ item }}"}, "loop": "{{ items }}"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_has_calls([
            mock.call(object=x) for x in [42, 43]
        ])

    def test_loop_register(self):
        items = [1, 2, None]
        defn = {"test": {"object": "{{ item }}"}, "loop": items,
                "register": "myvar"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_has_calls([
            mock.call(object=x) for x in items
        ])

        results = self.context["myvar"]
        self.assertEqual({"results"}, set(results))
        self.assertEqual(3, len(results["results"]))
        for item, value in zip(results["results"], items):
            self.assertIsInstance(item, miniscript.Result)
            self.assertTrue(item.succeeded)
            self.assertFalse(item.failed)
            self.assertFalse(item.skipped)
            self.assertEqual(value, item.result)

    def test_loop_skip(self):
        items = [1, 2, None]
        defn = {"test": {"object": "{{ item }}"}, "loop": items,
                "when": "item is not none", "register": "myvar"}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_has_calls([
            mock.call(object=x) for x in [1, 2]
        ])

        results = self.context["myvar"]
        self.assertEqual(3, len(results["results"]))
        for item, value in zip(results["results"], items):
            self.assertTrue(item.succeeded)
            self.assertFalse(item.failed)
            self.assertEqual(value is None, item.skipped)
            self.assertIsNone(item.failure)

    def test_loop_error(self):
        items = [1, None, 2]
        defn = {"test": {"object": "{{ item + 1 }}", "number": "{{ item }}"},
                "loop": items, "register": "myvar", "ignore_errors": True}
        task = TestTask("test", defn, self.engine)
        self.assertIsNone(task(self.context))
        task.side_effect.assert_has_calls([
            mock.call(object=x + 1) for x in [1, 2]
        ])

        results = self.context["myvar"]
        self.assertEqual(3, len(results["results"]))
        for item, value in zip(results["results"], items):
            self.assertEqual(value is not None, item.succeeded)
            self.assertEqual(value is None, item.failed)
            self.assertFalse(item.skipped)
            if value is None:
                self.assertIn("a number, not 'NoneType'", item.failure)
            else:
                self.assertIsNone(item.failure)
