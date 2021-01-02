import unittest
from unittest import mock

import miniscript
from miniscript import filters


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

    def test_flatten(self):
        in_list = [1, 2, [3, [4, 5, [6]], 7]]
        result = self.eval("in_list | flatten", in_list=in_list)
        self.assertEqual([1, 2, 3, 4, 5, 6, 7], result)

    def test_flatten_levels(self):
        in_list = [1, 2, [3, [4, 5, [6]], 7]]
        result = self.eval("in_list | flatten(levels=1)", in_list=in_list)
        self.assertEqual([1, 2, 3, [4, 5, [6]], 7], result)

    def test_difference(self):
        result = self.eval(
            "[2, 4, 6, 8, 12] | difference([3, 6, 9, 12, 15])")
        self.assertCountEqual([2, 4, 8], result)

    def test_intersect(self):
        result = self.eval(
            "[2, 4, 6, 8, 12] | intersect([3, 6, 9, 12, 15])")
        self.assertCountEqual([6, 12], result)

    def test_ipaddr(self):
        result = self.eval(
            "'192.168.35.1/24' | ipaddr('private') | ipaddr('address')")
        self.assertEqual('192.168.35.1', result)
        result = self.eval(
            "'2001:db8:32c::1/64' | ipaddr('private') | ipaddr('address')")
        self.assertEqual('2001:db8:32c::1', result)

    def test_ipv4(self):
        result = self.eval(
            "'192.168.35.1/24' | ipv4('private') | ipv4('address')")
        self.assertEqual('192.168.35.1', result)
        result = self.eval(
            "'2001:db8:32c::1/64' | ipv4('private') | ipv4('address')")
        self.assertIs(False, result)

    def test_ipv6(self):
        result = self.eval(
            "'192.168.35.1/24' | ipv6('private') | ipv6('address')")
        self.assertIs(False, result)
        result = self.eval(
            "'2001:db8:32c::1/64' | ipv6('private') | ipv6('address')")
        self.assertEqual('2001:db8:32c::1', result)

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

    @mock.patch.object(filters, 'jmespath', None)
    def test_json_query_unavailable(self):
        self.assertRaisesRegex(RuntimeError,
                               "requires jmespath",
                               self.eval,
                               "[] | json_query('[]')")

    def test_json_query(self):
        in_list = [
            {"name": "salad", "ingredients": {"tomatoes": 1, "cucumbers": 2}},
            {"name": "omelette", "ingredients": {"eggs": 3, "dill": 1}}
        ]
        result = self.eval(
            "in_list | json_query('[?ingredients.tomatoes > `0`] | [].name')",
            in_list=in_list)
        self.assertEqual(["salad"], result)

    def test_regex_escape(self):
        result = self.eval("'www.python.org' | regex_escape")
        self.assertEqual(r"www\.python\.org", result)

    def test_regex_findall(self):
        result = self.eval(
            "'http://www.python.org' | "
            r"regex_findall('(?<=\W)\w{3}(?=\W|$)')")
        self.assertEqual(['www', 'org'], result)

    def test_regex_findall_none(self):
        result = self.eval(
            "'http://www.python.org' | "
            r"regex_findall('(?<=\W)\w{4}(?=\W|$)')")
        self.assertEqual([], result)

    def test_regex_findall_case(self):
        result = self.eval(
            "'catCatCAT' | regex_findall('cat', ignorecase=True)")
        self.assertEqual(['cat', 'Cat', 'CAT'], result)
        result = self.eval(
            "'catCatCAT' | regex_findall('cat')")
        self.assertEqual(['cat'], result)

    def test_regex_replace(self):
        result = self.eval(
            "'http://www.python.org' | "
            "regex_replace('(?<=\\W)(\\w{3})(?=\\W|$)', '\"\\1\"')")
        self.assertEqual('http://"www".python."org"', result)

    def test_regex_replace_default(self):
        result = self.eval(
            "'http://www.python.org' | "
            "regex_replace('(?<=\\W)\\w{3}(?=\\W|$)')")
        self.assertEqual('http://.python.', result)

    def test_regex_replace_once(self):
        result = self.eval(
            "'http://www.python.org' | "
            "regex_replace('(?<=\\W)(\\w{3})(?=\\W|$)', '\"\\1\"', count=1)")
        self.assertEqual('http://"www".python.org', result)

    def test_regex_not_multiline(self):
        in_str = "x = 1\ny = 2"
        result = self.eval(
            "in_str | regex_replace('^', '## ')", in_str=in_str)
        self.assertEqual("## x = 1\ny = 2", result)

    def test_regex_multiline(self):
        in_str = "x = 1\ny = 2"
        result = self.eval(
            "in_str | regex_replace('^', '## ', multiline=True)",
            in_str=in_str)
        self.assertEqual("## x = 1\n## y = 2", result)

    def test_regex_search(self):
        result = self.eval(
            "'http://www.python.org/' | "
            "regex_search('(?<=\\W)\\w{3}(?=\\W)')")
        self.assertEqual('www', result)

    def test_regex_search_none(self):
        result = self.eval(
            "'http://www.python.org/' | "
            "regex_search('(?<=\\W)\\w{4}(?=\\W)')")
        self.assertEqual('', result)

    def test_regex_search_case(self):
        result = self.eval(
            "'CatcatCAT' | regex_search('cat', ignorecase=True)")
        self.assertEqual('Cat', result)
        result = self.eval(
            "'CatcatCAT' | regex_search('cat')")
        self.assertEqual('cat', result)

    def test_symmetric_difference(self):
        result = self.eval(
            "[2, 4, 6, 8, 12] | symmetric_difference([3, 6, 9, 12, 15])")
        self.assertCountEqual([2, 3, 4, 8, 9, 15], result)

    def test_to_datetime(self):
        result = self.eval(
            "(('2020-12-31 23:59:59' | to_datetime)"
            "- ('12/01/2020' | to_datetime('%m/%d/%Y'))).days")
        self.assertEqual(30, result)

    def test_union(self):
        result = self.eval(
            "[2, 4, 6, 8, 12] | union([3, 6, 9, 12, 15])")
        self.assertCountEqual([2, 3, 4, 6, 8, 9, 12, 15], result)

    def test_urlsplit(self):
        url = ("http://user:password@www.acme.com:9000/dir/index.html"
               "?query=term#fragment")
        result = self.eval(f"'{url}' | urlsplit")
        expected = {
            "fragment": "fragment",
            "hostname": "www.acme.com",
            "netloc": "user:password@www.acme.com:9000",
            "password": "password",
            "path": "/dir/index.html",
            "port": 9000,
            "query": "query=term",
            "scheme": "http",
            "username": "user"
        }
        self.assertEqual(expected, result)

    def test_urlsplit_component(self):
        url = ("http://user:password@www.acme.com:9000/dir/index.html"
               "?query=term#fragment")
        result = self.eval(f"'{url}' | urlsplit('netloc')")
        self.assertEqual("user:password@www.acme.com:9000", result)

    def test_urlsplit_unknown(self):
        self.assertRaisesRegex(AttributeError,
                               "Unknown URL component 'banana'",
                               self.eval,
                               "'http://example.com' | urlsplit('banana')")

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
