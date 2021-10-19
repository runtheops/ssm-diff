import unittest
import helpers


class TestFlatten(unittest.TestCase):
    def setUp(self):
        self.flatten = helpers.flatten

    def test_flatten_single(self):
        nested = {
            "key": "value"
        }
        flat = {
            "/key": "value",
        }
        self.assertEqual(flat, self.flatten(nested))

    def test_flatten_nested(self):
        nested = {
            'qa': {
                'ci': {
                    'api': {
                        'db_schema': 'foo_ci',
                        'db_user': 'bar_ci',
                        'db_password': 'baz_ci',
                    }
                },
                'uat': {
                    'api': {
                        'db_schema': 'foo_uat',
                        'db_user': 'bar_uat',
                        'db_password': 'baz_uat',
                    }
                }
            }
        }
        flat = {
            '/qa/ci/api/db_schema': 'foo_ci',
            '/qa/ci/api/db_user': 'bar_ci',
            '/qa/ci/api/db_password': 'baz_ci',
            '/qa/uat/api/db_schema': 'foo_uat',
            '/qa/uat/api/db_user': 'bar_uat',
            '/qa/uat/api/db_password': 'baz_uat',
        }
        self.assertEqual(flat, self.flatten(nested))

    def test_flatten_nested_with_internal_values(self):
        nested = {
            'a': {
                '@value': 'a_value',
                'b': {
                    '@value': 'b_value',
                    'c': {
                        '@value': 'c_value',
                        'key1': '1',
                        'key2': '2',
                        'key3': '3',
                    }
                }
            }
        }
        flat = {
            '/a': 'a_value',
            '/a/b': 'b_value',
            '/a/b/c': 'c_value',
            '/a/b/c/key1': '1',
            '/a/b/c/key2': '2',
            '/a/b/c/key3': '3',
        }
        self.assertEqual(flat, self.flatten(nested))


class TestAdd(unittest.TestCase):
    def setUp(self):
        self.add = helpers.add

    def test_add_single(self):
        obj = {}
        expected_obj = {'a': {'b': {'c': 'c_value'}}}
        self.add(obj, '/a/b/c', 'c_value')
        self.assertDictEqual(obj, expected_obj)

    def test_add_with_internal_values(self):
        obj = {}
        expected_obj = {
            'a': {
                '@value': 'a_value',
                'b': {
                    '@value': 'b_value',
                    'c': 'c_value',
                }
            }
        }
        self.add(obj, '/a', 'a_value')
        self.add(obj, '/a/b', 'b_value')
        self.add(obj, '/a/b/c', 'c_value')
        self.assertDictEqual(obj, expected_obj)


if __name__ == '__main__':
    unittest.main()