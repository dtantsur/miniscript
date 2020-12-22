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

import unittest

import yaml

import miniscript


class AddTask(miniscript.Task):
    required_params = {'values': list}
    singleton_param = 'values'

    def validate(self, params, context):
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
        result = engine.execute(code)
        self.assertEqual(90131, result)


class TestLongWithBuiltins(unittest.TestCase):
    """A test exercising built-ins a bit."""

    def test(self):
        with open('miniscript/tests/example-large.yaml') as fp:
            code = yaml.safe_load(fp)

        engine = miniscript.Engine({})
        result = engine.execute(code)
        self.assertEqual(42, result)
