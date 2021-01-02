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

    def test_assert(self):
        defn = {"assert": {"that": [
            "True",
            "banana is undefined",
            "40 + 2 == 42",
        ]}}
        task = tasks.Assert("assert", defn, self.engine)
        task(self.context)

    def test_assert_singleton(self):
        defn = {"assert": [
            "True",
            "banana is undefined",
            "40 + 2 == 42",
        ]}
        task = tasks.Assert("assert", defn, self.engine)
        task(self.context)

    def test_assert_fails(self):
        for value in ["False", "banana is defined", "40 + 2 == 100"]:
            with self.subTest(false_value=value):
                defn = {"assert": {"that": value}}
                task = tasks.Assert("assert", defn, self.engine)
                self.assertRaisesRegex(miniscript.ExecutionFailed,
                                       "evaluated to False",
                                       task, self.context)

    def test_assert_with_message(self):
        defn = {"assert": {"that": ["True", "False"],
                           "fail_msg": "I failed"}}
        task = tasks.Assert("assert", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "I failed", task, self.context)

    def test_assert_misconfigured(self):
        defn = {"assert": {"that": {},
                           "fail_msg": "I failed"}}
        task = tasks.Assert("assert", defn, self.engine)
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "must be a list or a string",
                               task, self.context)

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
