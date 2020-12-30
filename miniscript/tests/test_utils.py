import unittest

from miniscript import _utils


class TestIPFilter(unittest.TestCase):

    # Values from Ansible documentation
    values = ['192.24.2.1', 'host.fqdn', '::1', '192.168.32.0/24',
              'fe80::100/10', True, '', None,
              '42540766412265424405338506004571095040/64', '2130706433']
    results = ['192.24.2.1', False, '::1', '192.168.32.0/24', 'fe80::100/10',
               False, False, False, '2001:db8:32c:faad::/64', '127.0.0.1']

    def test_one(self):
        for item, result in zip(self.values, self.results):
            with self.subTest(item=item, expected=result):
                self.assertEqual(result, _utils.ip_filter(item))

    def test_values(self):
        valid = _utils.ip_filter(self.values)
        self.assertEqual(['192.24.2.1', '::1', '192.168.32.0/24',
                          'fe80::100/10', '2001:db8:32c:faad::/64',
                          '127.0.0.1'], valid)

    def test_version(self):
        v4 = _utils.ip_filter(self.values, version=4)
        self.assertEqual(['192.24.2.1', '192.168.32.0/24', '127.0.0.1'], v4)
        v6 = _utils.ip_filter(self.values, version=6)
        self.assertEqual(
            ['::1', 'fe80::100/10', '2001:db8:32c:faad::/64'], v6)

    def test_address(self):
        result = _utils.ip_filter('192.168.35.1/24', query='address')
        self.assertEqual('192.168.35.1', result)
        result = _utils.ip_filter(self.values, query='address')
        self.assertEqual(['192.24.2.1', '::1', 'fe80::100', '127.0.0.1'],
                         result)

    def test_host(self):
        result = _utils.ip_filter('192.168.35.1/24', query='host')
        self.assertEqual('192.168.35.1/24', result)
        result = _utils.ip_filter(self.values, query='host')
        self.assertEqual(['192.24.2.1/32', '::1/128', 'fe80::100/10',
                          '127.0.0.1/32'], result)

    def test_address_and_version(self):
        result = _utils.ip_filter(self.values, query='address', version=4)
        self.assertEqual(['192.24.2.1', '127.0.0.1'], result)
        result = _utils.ip_filter(self.values, query='address', version=6)
        self.assertEqual(['::1', 'fe80::100'], result)

    def test_address_type(self):
        result = _utils.ip_filter(self.values, query='public')
        self.assertEqual(['192.24.2.1'], result)
        result = _utils.ip_filter(self.values, query='private')
        self.assertEqual(['192.168.32.0/24', 'fe80::100/10',
                          '2001:db8:32c:faad::/64'], result)

    def test_net(self):
        result = _utils.ip_filter(self.values, query='net')
        self.assertEqual(['192.168.32.0/24', '2001:db8:32c:faad::/64'],
                         result)
        sizes = _utils.ip_filter(result, query='size')
        self.assertEqual([256, 18446744073709551616], sizes)

        ips = _utils.ip_filter(result, query='0')
        self.assertEqual(['192.168.32.0/24', '2001:db8:32c:faad::/64'], ips)
        ips = _utils.ip_filter(result, query='1')
        self.assertEqual(['192.168.32.1/24', '2001:db8:32c:faad::1/64'], ips)
        ips = _utils.ip_filter(result, query='-1')
        self.assertEqual(['192.168.32.255/24',
                          '2001:db8:32c:faad:ffff:ffff:ffff:ffff/64'], ips)

    def test_range(self):
        result = _utils.ip_filter(self.values, query='192.0.0.0/8')
        self.assertEqual(['192.24.2.1', '192.168.32.0/24'], result)

    def test_unknown(self):
        self.assertRaises(TypeError, _utils.ip_filter, self.values, query='??')
