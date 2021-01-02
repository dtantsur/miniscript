import unittest

import yaml

import miniscript


class AddTask(miniscript.Task):
    required_params = {'values': list}
    singleton_param = 'values'

    def validate(self, params, context):
        super().validate(params, context)
        for item in params['values']:
            int(item)

    def execute(self, params, context):
        return {"sum": sum(params['values'])}


class FunctionalTests(unittest.TestCase):

    def test_from_docs(self):
        """A test based on Engine docs."""
        with open('miniscript/tests/example-docs.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({'add': AddTask})
        context = miniscript.Context(engine, values=[23423, 43874, 22834])
        result = engine.execute(code, context)
        self.assertEqual(90131, result)

    def test_long_with_builtins(self):
        """A test exercising built-ins a bit."""
        with open('miniscript/tests/example-large.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({})
        result = engine.execute(code)
        self.assertEqual({'decrypted': 42, 'params': {'random': 13}}, result)
        # No contexts or namespaces in the result!
        self.assertIs(type(result), dict)
        self.assertIs(type(result['params']), dict)

    def test_slashes_handling(self):
        """Test ansible-compatible slashes handling."""
        with open('miniscript/tests/ansible_bug_11891.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({})
        result = engine.execute(code)
        self.assertEqual({"value1": "\\1", "value2": "test"}, result)
        self.assertIs(type(result), dict)
