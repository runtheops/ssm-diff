from unittest import TestCase, mock

from . import engine


class FlatDictDiffer(TestCase):

    def setUp(self) -> None:
        self.obj = engine.DiffResolver({}, {})

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


class DiffResolverMerge(TestCase):

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

        plan = engine.DiffResolver(
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

        diff = engine.DiffResolver(
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

        args = mock.Mock(force=True)
        diff = engine.DiffResolver.configure(args )(
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

        args = mock.Mock(force=False)
        diff = engine.DiffResolver.configure(args)(
            remote,
            local,
        )

        self.assertEqual(
            local,
            diff.merge()
        )


class DiffResolverPlan(TestCase):

    def test_add(self):
        """The basic engine will mark any keys present in local but not remote as an add"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
            'x': {'y': {'z': 'x/y/z'}}
        }

        diff = engine.DiffResolver(
            remote,
            local,
        )

        self.assertDictEqual(
            {
                'add': {
                    '/x/y/z': 'x/y/z',
                },
                'delete': {},
                'change': {}
            },
            diff.plan
        )

    def test_change(self):
        """The basic engine will mark any keys that differ between remote and local as a change"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d_new'}},
        }

        diff = engine.DiffResolver(
            remote,
            local,
        )

        self.assertDictEqual(
            {
                'add': {},
                'delete': {},
                'change': {
                    '/a/b/d': {'old': 'a/b/d', 'new': 'a/b/d_new'}
                }
            },
            diff.plan
        )

    def test_delete(self):
        """The basic engine will mark any keys present in remote but not local as a delete"""
        remote = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
            'x': {'y': {'z': 'x/y/z'}}
        }
        local = {
            'a': {'b': {'c': 'a/b/c',
                        'd': 'a/b/d'}},
        }

        diff = engine.DiffResolver(
            remote,
            local,
        )

        self.assertDictEqual(
            {
                'add': {},
                'delete': {
                    '/x/y/z': 'x/y/z',
                },
                'change': {}
            },
            diff.plan
        )
