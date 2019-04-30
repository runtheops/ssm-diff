from unittest import TestCase

from . import helpers


class FlatDictDiffer(TestCase):

    def setUp(self) -> None:
        self.obj = helpers.DiffResolver({}, {})

    def test_flatten_single(self):
        nested = {
            "key": "value"
        }
        flat = {
            "/key": "value",
        }
        self.assertEqual(
            flat,
            self.obj._flatten(nested)
        )
        self.assertEqual(
            nested,
            self.obj._unflatten(flat)
        )

    def test_flatten_nested(self):
        nested = {
            "key1": {
                "key2": "value"
            }
        }
        flat = {
            "/key1/key2": "value",
        }
        self.assertEqual(
            flat,
            self.obj._flatten(nested)
        )
        self.assertEqual(
            nested,
            self.obj._unflatten(flat)
        )

    def test_flatten_nested_sep(self):
        nested = {
            "key1": {
                "key2": "value"
            }
        }
        flat = {
            "\\key1\\key2": "value",
        }
        self.assertEqual(
            flat,
            self.obj._flatten(nested, sep='\\')
        )
        self.assertEqual(
            nested,
            self.obj._unflatten(flat, sep='\\')
        )


class Pull(TestCase):

    def test_add_remote(self):
        """Remote additions should be added to local"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
            'x': {'y': {'z': 'x/y/z'}}
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }

        plan = helpers.DiffResolver(
            remote,
            local,
        )

        self.assertEqual(
            remote,
            plan.merge()
        )

    def test_add_local(self):
        """Local additions should be preserved so we won't see any changes to local"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
            'x': {'y': {'z': 'x/y/z'}}
        }

        diff = helpers.DiffResolver(
            remote,
            local,
        )

        self.assertEqual(
            local,
            diff.merge()
        )

    def test_change_local_force(self):
        """Local changes should be overwritten if force+True"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d_new'}},
        }

        diff = helpers.DiffResolver.configure(force=True)(
            remote,
            local,
        )

        self.assertEqual(
            remote,
            diff.merge()
        )

    def test_change_local_no_force(self):
        """Local changes should be preserved if force=False"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d_new'}},
        }

        diff = helpers.DiffResolver.configure(force=False)(
            remote,
            local,
        )

        self.assertEqual(
            local,
            diff.merge()
        )
