import json
import random
import string
from unittest import TestCase, mock

import yaml

from . import engine, storage


class DiffBaseFlatten(TestCase):
    """Verifies the behavior of the _flatten and _unflatten methods"""
    def setUp(self) -> None:
        self.obj = engine.DiffBase({}, {})

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
    """Verifies that the `merge` method produces the expected output"""

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


class YAMLFileValidatePaths(TestCase):
    """YAMLFile calls `validate_paths` in `__init__` to ensure the root and paths are compatible"""
    def test_validate_paths_invalid(self):
        with self.assertRaises(ValueError):
            storage.YAMLFile(filename='unused', root_path='/one/branch', paths=['/another/branch'])

    def test_validate_paths_valid_same(self):
        self.assertIsInstance(
            storage.YAMLFile(filename='unused', root_path='/one/branch', paths=['/one/branch']),
            storage.YAMLFile,
        )

    def test_validate_paths_valid_child(self):
        self.assertIsInstance(
            storage.YAMLFile(filename='unused', root_path='/one/branch', paths=['/one/branch/child']),
            storage.YAMLFile,
        )


class YAMLFileMetadata(TestCase):
    """Verifies that exceptions are thrown if the metadata in the target file is incompatible with the class configuration"""
    def test_get_methods(self):
        """Make sure we use the methods mocked by other tests"""
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        provider = storage.YAMLFile(filename=filename, no_secure=True)
        with mock.patch('states.storage.open') as open_, mock.patch('states.storage.yaml') as yaml, \
                mock.patch.object(provider, 'validate_config'):
            self.assertEqual(
                provider.get(),
                yaml.safe_load.return_value,
            )
            open_.assert_called_once_with(
                filename + '.yml', 'rb'
            )
            yaml.safe_load.assert_called_once_with(
                open_.return_value.__enter__.return_value.read.return_value
            )

    def test_get_invalid_no_secure(self):
        """Exception should be raised if the secure metadata in the file does not match the instance"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_NO_SECURE: False
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        provider = storage.YAMLFile(filename=filename, no_secure=True)

        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            with self.assertRaises(ValueError):
                provider.get()

    def test_get_valid_no_secure(self):
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_NO_SECURE: False
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        provider = storage.YAMLFile(filename=filename, no_secure=False)

        with mock.patch('states.storage.open') as open_, mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            self.assertEqual(
                provider.get(),
                yaml.safe_load.return_value,
            )

    def test_get_valid_no_secure_true(self):
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_NO_SECURE: True
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        provider = storage.YAMLFile(filename=filename, no_secure=True)

        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            self.assertEqual(
                provider.get(),
                yaml.safe_load.return_value,
            )

    def test_get_invalid_root(self):
        """Exception should be raised if the root metadata in the file does not match the instance"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_ROOT: '/'
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        with mock.patch.object(storage.YAMLFile, 'validate_paths'):
            provider = storage.YAMLFile(filename=filename, root_path='/another')

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            with self.assertRaises(ValueError):
                provider.get()

    def test_get_valid_root(self):
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_ROOT: '/same'
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        with mock.patch.object(storage.YAMLFile, 'validate_paths'):
            provider = storage.YAMLFile(filename=filename, root_path='/same')

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml, \
                mock.patch.object(provider, 'nest_root'):
            yaml.safe_load.return_value = yaml_contents
            provider.get()

    def test_get_invalid_paths(self):
        """Exception should be raised if the paths metadata is incompatible with the instance"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/limited']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths='/')

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            with self.assertRaises(ValueError):
                provider.get()

    def test_get_invalid_paths_mixed(self):
        """A single invalid path should fail even in the presence of multiple matching paths"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/limited']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/', '/limited'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            with self.assertRaises(ValueError):
                provider.get()

    def test_get_invalid_paths_multiple(self):
        """Multiple invalid paths should fail"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/limited']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/', '/another'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            with self.assertRaises(ValueError):
                provider.get()

    def test_get_valid_paths_same(self):
        """The same path is valid"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            provider.get()

    def test_get_valid_paths_child(self):
        """A descendant (child) of a path is valid since it's contained in the original"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/child'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            provider.get()

    def test_get_valid_paths_child_multiple(self):
        """Multiple descendant (child) of a path is valid since it's contained in the original"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                storage.YAMLFile.METADATA_PATHS: ['/']
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/child', '/another_child'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            provider.get()

    def test_get_valid_paths_default_nested(self):
        """The default path is '/' so it should be valid for anything"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/child'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            provider.get()

    def test_get_valid_paths_default_root(self):
        """The default path is '/' so it should be valid for anything"""
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
            }
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, paths=['/'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            provider.get()


class YAMLFileRoot(TestCase):
    """Verify that the `root_path` config works as expected"""
    def test_unnest_path(self):
        yaml_contents = {
            storage.YAMLFile.METADATA_CONFIG: {
                # must match root_path of object to pass checks
                storage.YAMLFile.METADATA_ROOT: '/nested/path'
            },
            'key': 'value'
        }
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, root_path='/nested/path', paths=['/nested/path'])

        # handle open/yaml processing
        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            yaml.safe_load.return_value = yaml_contents
            self.assertEqual(
                {
                    'nested': {
                        'path': {
                            'key': 'value'
                        }
                    }
                },
                provider.get(),
            )

    def test_nest_path(self):
        filename = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        # make sure validate_paths isn't run
        provider = storage.YAMLFile(filename=filename, root_path='/nested/path', paths=['/nested/path'])

        with mock.patch('states.storage.open'), mock.patch('states.storage.yaml') as yaml:
            provider.save({
                'nested': {
                    'path': {
                        'key': 'value'
                    }
                }
            })

        yaml.safe_dump.assert_called_once_with(
            {
                storage.YAMLFile.METADATA_CONFIG: {
                    storage.YAMLFile.METADATA_ROOT: '/nested/path',
                    storage.YAMLFile.METADATA_PATHS: ['/nested/path'],
                    storage.YAMLFile.METADATA_NO_SECURE: False,
                },
                'key': 'value'
            },
            # appears to replicate a default, but included in the current code
            default_flow_style=False
        )


class JSONBranch(TestCase):
    def test_eq(self):
        test_struture = {'test': ['imem1', 'item2']}
        test_node = yaml.safe_dump(test_struture)
        obj = storage.JSONBranch.from_yaml(yaml, test_node)
        self.assertEqual(
            obj.value,
            test_struture,
        )
        self.assertEqual(
            obj,
            json.dumps(test_struture),
        )
