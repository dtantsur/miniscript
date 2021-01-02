import unittest

import miniscript
from miniscript import _context


class EnvironmentTestCase(unittest.TestCase):

    engine = miniscript.Engine({})
    env = engine.environment

    def test_evaluate(self):
        context = miniscript.Context(self.engine, answer=42)
        result = self.env.evaluate("answer is {{answer}}", context)
        self.assertEqual("answer is 42", result)

    def test_evaluate_with_quotes(self):
        context = miniscript.Context(self.engine, answer='"42"!')
        result = self.env.evaluate("answer is {{answer}}", context)
        self.assertEqual('answer is "42"!', result)

    def test_evaluate_recursive(self):
        data = {
            "answer": 42,
            "text": "answer is {{ answer }}",
            "key": {
                "value": "{{ list }}"
            },
            "list": [
                "{{ answer }}",
                "{{ answer * 10 }}",
                "{{ text | upper }}"
            ]
        }
        context = miniscript.Context(self.engine, data)
        result = self.env.evaluate_recursive("{{ key }}", context)
        self.assertEqual([42, 420, 'ANSWER IS 42'], result["value"])
        result = self.env.evaluate_recursive(result, context)
        self.assertEqual([42, 420, 'ANSWER IS 42'], result["value"])

    def test_evaluate_recursive_infinite(self):
        data = {
            "key": "{{ indirect }}",
            "value": {
                "key": "{{ key }}"
            },
            "indirect": ["{{ value }}"],
        }
        # It is safe to create recursive dicts
        context = miniscript.Context(self.engine, data)
        result = self.env.evaluate_recursive("{{ value }}", context)
        self.assertIsInstance(result, _context.Namespace)

    def test_evaluate_slashes_fixup(self):
        expr = r"A slash outside \ {{ '\foo\\' | replace('f', '\1') }}"
        context = miniscript.Context(self.engine)
        result = self.env.evaluate(expr, context)
        self.assertEqual(r"A slash outside \ \\1oo\\", result)


class ContextTestCase(unittest.TestCase):

    engine = miniscript.Engine({})

    def test_simple(self):
        ctx = miniscript.Context(self.engine, {"key": "value"})
        self.assertEqual("value", ctx["key"])
        self.assertRaises(KeyError, ctx.__getitem__, "foo")

    def test_string(self):
        data = {"answer": 42, "key": "answer is {{ answer }}"}
        ctx = miniscript.Context(self.engine, data)
        self.assertEqual("answer is 42", ctx["key"])

    def test_complex(self):
        data = {
            "answer": 42,
            "text": "answer is {{ answer }}",
            "key": {
                "value": "{{ text | upper }}"
            }
        }
        ctx = miniscript.Context(self.engine, data)
        sub_ctx = ctx["key"]
        self.assertIsInstance(sub_ctx, _context.Namespace)
        self.assertEqual("ANSWER IS 42", sub_ctx["value"])

    def test_iter(self):
        ctx = miniscript.Context(self.engine, {"key": "value"})
        self.assertEqual(["key"], list(ctx))

    def test_eq(self):
        ctx = miniscript.Context(self.engine, {"key": "value"})
        self.assertEqual({"key": "value"}, ctx)

    def test_set_del(self):
        ctx = miniscript.Context(self.engine, {"key": "value"})
        ctx["key"] = "value2"
        self.assertEqual({"key": "value2"}, ctx)
        del ctx["key"]
        self.assertEqual({}, ctx)

    def test_copy(self):
        orig = {"key": "value", "dict": {}}
        ctx = miniscript.Context(self.engine, orig.copy())

        copy = ctx.copy()
        copy["key"] = "value2"
        self.assertEqual(orig, ctx)

        ns = ctx["dict"].copy()
        ns["key"] = "value3"
        self.assertEqual(orig, ctx)
