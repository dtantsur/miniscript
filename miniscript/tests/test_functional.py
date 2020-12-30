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


class TestFromDocs(unittest.TestCase):
    """A test based on Engine docs."""

    def test(self):
        with open('miniscript/tests/example-docs.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({'add': AddTask})
        context = miniscript.Context(engine, values=[23423, 43874, 22834])
        result = engine.execute(code, context)
        self.assertEqual(90131, result)


class TestLongWithBuiltins(unittest.TestCase):
    """A test exercising built-ins a bit."""

    def test(self):
        with open('miniscript/tests/example-large.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({})
        result = engine.execute(code)
        self.assertEqual(42, result)
