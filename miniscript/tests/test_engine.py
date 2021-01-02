import logging
import typing
import unittest
from unittest import mock

import miniscript
from miniscript import _types
from miniscript import tasks


class TestTask(miniscript.Task):
    def execute(
        self,
        params: typing.Mapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        context["answer"] = 42


class FinishTask(miniscript.Task):
    optional_params = {'value': None}

    def execute(
        self,
        params: typing.Mapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        raise _types.FinishScript(params.get('value', 42))


class FailTask(miniscript.Task):
    def execute(
        self,
        params: typing.Mapping[str, typing.Any],
        context: miniscript.Context,
    ) -> None:
        raise RuntimeError("I'm tired")


class EngineTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.engine = miniscript.Engine({"test": TestTask,
                                         "finish": FinishTask,
                                         "fail": FailTask})

    def test_no_tasks(self):
        engine = miniscript.Engine()
        self.assertEqual({'assert', 'block', 'fail', 'log', 'return', 'vars'},
                         set(engine.tasks))
        # Sanity-check: everything in tasks is exposed.
        for item in dir(tasks):
            if isinstance(getattr(tasks, item), typing.Type):
                self.assertIn(item.lower(), engine.tasks)

    def test_builtin_tasks(self):
        expected = {'assert', 'block', 'fail', 'log', 'return', 'vars'}
        self.assertEqual(expected, expected.intersection(self.engine.tasks))
        # Sanity-check: everything in tasks is exposed.
        for item in dir(tasks):
            if isinstance(getattr(tasks, item), typing.Type):
                self.assertIn(item.lower(), self.engine.tasks)

    def test_logger(self):
        self.assertIsInstance(self.engine.logger, logging.Logger)
        logger = logging.getLogger(__name__)
        engine = miniscript.Engine({}, logger=logger)
        self.assertIs(logger, engine.logger)

    def test_forbidden_names(self):
        for name in miniscript.Task._KNOWN_PARAMETERS:
            with self.subTest(name=name):
                self.assertRaises(ValueError, miniscript.Engine,
                                  {name: TestTask})

    def test_no_additional_filters(self):
        engine = miniscript.Engine({}, additional_filters=False)
        self.assertNotIn('dict2items', engine.environment.filters)

    def test_tasks_required(self):
        self.assertRaisesRegex(miniscript.InvalidScript,
                               "task is required",
                               self.engine.execute, [])

    def test_tasks_invalid_type(self):
        self.assertRaisesRegex(miniscript.InvalidScript,
                               "must be a list, got 42",
                               self.engine.execute, {"tasks": 42})

    def test_tasks_extra_options(self):
        self.assertRaisesRegex(miniscript.InvalidScript,
                               "Only tasks .*, got foo",
                               self.engine.execute,
                               {"tasks": [{"test": None}], "foo": 42})

    def test_tasks_unknown_task(self):
        self.assertRaises(miniscript.UnknownTask,
                          self.engine.execute,
                          [{"test": None}, {"foo": None}])

    def test_tasks_ambiguous(self):
        self.assertRaises(miniscript.InvalidTask,
                          self.engine.execute,
                          [{"test": None, "finish": None}])

    @mock.patch.object(TestTask, 'execute', autospec=True, return_value=None)
    def test_execute(self, mock_execute):
        result = self.engine.execute({"tasks": [{"test": None}]})
        self.assertIsNone(result)
        mock_execute.assert_called_once_with(mock.ANY, {}, mock.ANY)

    @mock.patch.object(TestTask, 'execute', autospec=True, return_value=None)
    def test_execute_list(self, mock_execute):
        result = self.engine.execute([{"test": None}])
        self.assertIsNone(result)
        mock_execute.assert_called_once_with(mock.ANY, {}, mock.ANY)

    def test_execute_context(self):
        context = miniscript.Context(self.engine)
        self.engine.execute([{"test": None}], context)
        self.assertEqual(42, context["answer"])

    def test_execute_finish(self):
        result = self.engine.execute([{"finish": None}])
        self.assertEqual(42, result)

    def test_execute_finish_undefined(self):
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "Script returned undefined value",
                               self.engine.execute,
                               [{"finish": {'value': '{{ invalid }}'}}])

    def test_execute_finish_invalid(self):
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "'invalid' is undefined",
                               self.engine.execute,
                               [{"finish": {'value': '{{ invalid + 1 }}'}}])

    def test_execute_fail(self):
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "fail.*I'm tired",
                               self.engine.execute, [{"fail": None}])

    @mock.patch.object(miniscript.Task, '__call__', autospec=True)
    def test_execute_fail_unexpected(self, mock_call):
        mock_call.side_effect = KeyError("unexpected")
        self.assertRaisesRegex(miniscript.ExecutionFailed,
                               "KeyError: 'unexpected'",
                               self.engine.execute, [{"fail": None}])
