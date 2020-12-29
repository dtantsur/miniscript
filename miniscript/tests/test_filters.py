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

import miniscript


class TestFilters(unittest.TestCase):

    engine = miniscript.Engine({})
    env = engine.environment

    def eval(self, expr: str, **ctx):
        context = miniscript.Context(self.engine, ctx)
        return self.env.evaluate_code(expr, context)

    def test_bool_from_string(self):
        for true_val in ['true', 'True', 'yes', 'Yes', 'YES', '1']:
            with self.subTest(value=true_val):
                result = self.eval(f"'{true_val}' | bool")
                self.assertIs(True, result)
        for false_val in ['false', 'False', 'no', 'No', 'NOOO', '0', 'banana']:
            with self.subTest(value=false_val):
                result = self.eval(f"'{false_val}' | bool")
                self.assertIs(False, result)

    def test_bool_from_other(self):
        for true_val in ['1', 'True', 'true']:
            with self.subTest(value=true_val):
                result = self.eval(f"{true_val} | bool")
                self.assertIs(True, result)
        for false_val in ['false', 'False', '0', '{}']:
            with self.subTest(value=false_val):
                result = self.eval(f"{false_val} | bool")
                self.assertIs(False, result)

    def test_combine(self):
        in_dict = {"milk": 1, "eggs": 10}
        update = {"milk": 2, "bread": 1}
        result = self.eval("in_dict | combine(update)",
                           in_dict=in_dict, update=update)
        self.assertEqual({"milk": 2, "bread": 1, "eggs": 10}, result)
        # The original dicts have not been changed
        self.assertEqual({"milk": 1, "eggs": 10}, in_dict)
        self.assertEqual({"milk": 2, "bread": 1}, update)

    def test_combine_wrong_list_merge(self):
        self.assertRaisesRegex(TypeError,
                               "'foo' is not a valid list_merge value",
                               self.eval, "{} | combine({}, list_merge='foo')")

    def test_combine_empty(self):
        result = self.eval("[] | combine()")
        self.assertEqual({}, result)

    def test_combine_from_empty(self):
        update = {"milk": 2, "bread": 1}
        result = self.eval("[] | combine(update)", update=update)
        self.assertEqual({"milk": 2, "bread": 1}, result)

    def test_combine_from_many(self):
        in_dict = [{"milk": 1, "eggs": 10}, {"eggs": 20, "bread": 3}]
        update = {"milk": 2, "bread": 1}
        result = self.eval("in_dict | combine(update)",
                           in_dict=in_dict, update=update)
        self.assertEqual({"milk": 2, "bread": 1, "eggs": 20}, result)

    def test_combine_with_many(self):
        in_dict = {"milk": 1, "eggs": 10}
        update1 = {"milk": 2, "bread": 1}
        update2 = {"bread": 3}
        result = self.eval("in_dict | combine(update1, update2)",
                           in_dict=in_dict, update1=update1, update2=update2)
        self.assertEqual({"milk": 2, "bread": 3, "eggs": 10}, result)

    def test_combine_non_recursive(self):
        in_dict = {"answer": 42, "non-answer": 0,
                   "nested": {"key": "value", "key2": "value2"}}
        update = {"non-answer": None, "nested": {"key": "another value"},
                  "added": {"key": "value3"}}
        result = self.eval("in_dict | combine(update)",
                           in_dict=in_dict, update=update)
        self.assertEqual({"answer": 42, "non-answer": None,
                          "nested": {"key": "another value"},
                          "added": {"key": "value3"}}, result)

    def test_combine_recursive(self):
        in_dict = {"answer": 42, "non-answer": 0,
                   "nested": {"key": "value", "key2": "value2"}}
        update = {"non-answer": None, "nested": {"key": "another value"},
                  "added": {"key": "value3"}}
        result = self.eval("in_dict | combine(update, recursive=True)",
                           in_dict=in_dict, update=update)
        self.assertEqual({"answer": 42, "non-answer": None,
                          "nested": {"key": "another value",
                                     "key2": "value2"},
                          "added": {"key": "value3"}}, result)

    def test_combine_lists(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval("in_dict | combine(update)",
                           in_dict=in_dict, update=update)
        self.assertEqual({"items": [3, 6, 9]}, result)

    def test_combine_lists_keep(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval("in_dict | combine(update, list_merge='keep')",
                           in_dict=in_dict, update=update)
        self.assertEqual({"items": [1, 2, 3, 4]}, result)

    def test_combine_lists_append(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval("in_dict | combine(update, list_merge='append')",
                           in_dict=in_dict, update=update)
        self.assertEqual({"items": [1, 2, 3, 4, 3, 6, 9]}, result)

    def test_combine_lists_prepend(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval("in_dict | combine(update, list_merge='prepend')",
                           in_dict=in_dict, update=update)
        self.assertEqual({"items": [3, 6, 9, 1, 2, 3, 4]}, result)

    def test_combine_lists_append_rp(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval("in_dict | combine(update, list_merge='append_rp')",
                           in_dict=in_dict, update=update)
        self.assertEqual({"items": [1, 2, 4, 3, 6, 9]}, result)

    def test_combine_lists_prepend_rp(self):
        in_dict = {"items": [1, 2, 3, 4]}
        update = {"items": [3, 6, 9]}
        result = self.eval(
            "in_dict | combine(update, list_merge='prepend_rp')",
            in_dict=in_dict, update=update)
        self.assertEqual({"items": [3, 6, 9, 1, 2, 4]}, result)

    def test_dict2items(self):
        in_dict = {"milk": 1, "eggs": 10}
        result = self.eval("in_dict | dict2items", in_dict=in_dict)
        self.assertIsInstance(result, list)
        result = sorted(result, key=lambda item: item['key'])
        self.assertEqual([{"key": "eggs", "value": 10},
                          {"key": "milk", "value": 1}],
                         result)

    def test_dict2items_customized(self):
        in_dict = {"milk": 1, "eggs": 10}
        result = self.eval(
            "in_dict | dict2items(key_name='item',value_name='qty')",
            in_dict=in_dict)
        self.assertIsInstance(result, list)
        result = sorted(result, key=lambda item: item['item'])
        self.assertEqual([{"item": "eggs", "qty": 10},
                          {"item": "milk", "qty": 1}],
                         result)

    def test_items2dict(self):
        in_list = [{"key": "eggs", "value": 10},
                   {"key": "milk", "value": 1}]
        result = self.eval("in_list | items2dict", in_list=in_list)
        self.assertEqual({"milk": 1, "eggs": 10}, result)

    def test_items2dict_customized(self):
        in_list = [{"item": "eggs", "qty": 10},
                   {"item": "milk", "qty": 1}]
        result = self.eval(
            "in_list | items2dict(key_name='item',value_name='qty')",
            in_list=in_list)
        self.assertEqual({"milk": 1, "eggs": 10}, result)

    def test_zip(self):
        qtys = [10, 1]
        result = self.eval(
            '["eggs", "milk", "bread"] | zip(qtys) | list', qtys=qtys)
        self.assertEqual([("eggs", 10), ("milk", 1)], result)

    def test_zip_longest(self):
        qtys = [10, 1]
        result = self.eval(
            '["eggs", "milk", "bread"] | zip_longest(qtys, fillvalue=0) '
            '| list', qtys=qtys)
        self.assertEqual([("eggs", 10), ("milk", 1), ("bread", 0)], result)
