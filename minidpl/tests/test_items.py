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

import minidpl


class RealItem(minidpl.Item):
    pass


class TestItem(unittest.TestCase):

    item = RealItem()

    def test_process_params(self):
        self.assertEqual(
            {'value': 42, 'another': 'none'},
            self.item.process_params({'value': 42}, {'another': 'none'}, None))

    def test_process_params_fails(self):
        for value in [None, 42, "string", ["list"]]:
            with self.subTest(top_level=value):
                self.assertRaises(TypeError, self.item.process_params,
                                  value, {}, None)
            with self.subTest(internal=value):
                self.assertRaises(TypeError, self.item.process_params,
                                  {}, value, None)
