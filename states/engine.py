import collections
import logging
import re
from functools import partial

from termcolor import colored

from .helpers import add


class DiffMount(type):
    """Metaclass for Diff plugin system"""
    # noinspection PyUnusedLocal,PyMissingConstructor
    def __init__(cls, *args, **kwargs):
        if not hasattr(cls, 'plugins'):
            cls.plugins = dict()
        else:
            cls.plugins[cls.__name__] = cls


class DiffBase(metaclass=DiffMount):
    """Superclass for diff plugins"""
    def __init__(self, remote, local):
        self.logger = logging.getLogger(self.__module__)
        self.remote_flat, self.local_flat = self._flatten(remote), self._flatten(local)
        self.remote_set, self.local_set = set(self.remote_flat.keys()), set(self.local_flat.keys())

    # noinspection PyUnusedLocal
    @classmethod
    def get_plugin(cls, name):
        if name in cls.plugins:
            return cls.plugins[name]

    @classmethod
    def configure(cls, args):
        """Extract class-specific configurations from CLI args and pre-configure the __init__ method using functools.partial"""
        return cls

    @classmethod
    def _flatten(cls, d, current_path='', sep='/'):
        """Convert a nested dict structure into a "flattened" dict i.e. {"full/path": "value", ...}"""
        items = {}
        for k, v in d.items():
            new = current_path + sep + k if current_path else k
            if isinstance(v, collections.MutableMapping):
                items.update(cls._flatten(v, new, sep=sep).items())
            else:
                items[sep + new] = v
        return items

    @classmethod
    def _unflatten(cls, d, sep='/'):
        """Converts a "flattened" dict i.e. {"full/path": "value", ...} into a nested dict structure"""
        output = {}
        for k, v in d.items():
            add(
                obj=output,
                path=k,
                value=v,
                sep=sep,
            )
        return output

    @classmethod
    def describe_diff(cls, plan):
        """Return a (multi-line) string describing all differences"""
        description = ""
        for k, v in plan['add'].items():
            # { key: new_value }
            description += colored("+", 'green') + "{} = {}".format(k, v) + '\n'

        for k in plan['delete']:
            # { key: old_value }
            description += colored("-", 'red') + k + '\n'

        for k, v in plan['change'].items():
            # { key: {'old': value, 'new': value} }
            description += colored("~", 'yellow') + "{}:\n\t< {}\n\t> {}".format(k, v['old'], v['new']) + '\n'

        if description == "":
            description = "No Changes Detected"

        return description

    @property
    def plan(self):
        """Returns a `dict` of operations for updating the remote storage i.e. {'add': {...}, 'change': {...}, 'delete': {...}}"""
        raise NotImplementedError

    def merge(self):
        """Generate a merge of the local and remote dicts, following configurations set during __init__"""
        raise NotImplementedError


class DiffResolver(DiffBase):
    """Determines diffs between two dicts, where the remote copy is considered the baseline"""
    def __init__(self, remote, local, force=False):
        super().__init__(remote, local)
        self.intersection = self.remote_set.intersection(self.local_set)
        self.force = force

        if self.added() or self.removed() or self.changed():
            self.differ = True
        else:
            self.differ = False

    @classmethod
    def configure(cls, args):
        kwargs = {}
        if hasattr(args, 'force'):
            kwargs['force'] = args.force
        return partial(cls, **kwargs)

    def added(self):
        """Returns a (flattened) dict of added leaves i.e. {"full/path": value, ...}"""
        return self.local_set - self.intersection

    def removed(self):
        """Returns a (flattened) dict of removed leaves i.e. {"full/path": value, ...}"""
        return self.remote_set - self.intersection

    def changed(self):
        """Returns a (flattened) dict of changed leaves i.e. {"full/path": value, ...}"""
        return set(k for k in self.intersection if self.remote_flat[k] != self.local_flat[k])

    def unchanged(self):
        """Returns a (flattened) dict of unchanged leaves i.e. {"full/path": value, ...}"""
        return set(k for k in self.intersection if self.remote_flat[k] == self.local_flat[k])

    @property
    def plan(self):
        return {
            'add': {
                k: self.local_flat[k] for k in self.added()
            },
            'delete': {
                k: self.remote_flat[k] for k in self.removed()
            },
            'change': {
                k: {'old': self.remote_flat[k], 'new': self.local_flat[k]} for k in self.changed()
            }
        }

    def merge(self):
        dictfilter = lambda original, keep_keys: dict([(i, original[i]) for i in original if i in set(keep_keys)])
        if self.force:
            # Overwrite local changes (i.e. only preserve added keys)
            # NOTE:  Currently the system cannot tell the difference between a remote delete and a local add
            prior_set = self.changed().union(self.removed()).union(self.unchanged())
            current_set = self.added()
        else:
            # Preserve added keys and changed keys
            # NOTE:  Currently the system cannot tell the difference between a remote delete and a local add
            prior_set = self.unchanged().union(self.removed())
            current_set = self.added().union(self.changed())
        state = dictfilter(original=self.remote_flat, keep_keys=prior_set)
        state.update(dictfilter(original=self.local_flat, keep_keys=current_set))
        return self._unflatten(state)
