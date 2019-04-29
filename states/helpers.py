import collections
from copy import deepcopy
from functools import partial

from termcolor import colored


class DiffResolver(object):
    """Determines diffs between two dicts, where the remote copy is considered the baseline"""
    def __init__(self, remote, local, force=False):
        self.remote_flat, self.local_flat = self._flatten(remote), self._flatten(local)
        self.remote_set, self.local_set = set(self.remote_flat.keys()), set(self.local_flat.keys())
        self.intersection = self.remote_set.intersection(self.local_set)
        self.force = force

        if self.added() or self.removed() or self.changed():
            self.differ = True
        else:
            self.differ = False

    @classmethod
    def configure(cls, *args, **kwargs):
        return partial(cls, *args, **kwargs)

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

    def describe_diff(self):
        """Return a (multi-line) string describing all differences"""
        description = ""
        for k in self.added():
            description += colored("+", 'green'), "{} = {}".format(k, self.local_flat[k]) + '\n'

        for k in self.removed():
            description += colored("-", 'red'), k + '\n'

        for k in self.changed():
            description += colored("~", 'yellow'), "{}:\n\t< {}\n\t> {}".format(k, self.remote_flat[k], self.local_flat[k]) + '\n'

        return description

    def _flatten(self, d, current_path='', sep='/'):
        """Convert a nested dict structure into a "flattened" dict i.e. {"full/path": "value", ...}"""
        items = []
        for k in d:
            new = current_path + sep + k if current_path else k
            if isinstance(d[k], collections.MutableMapping):
                items.extend(self._flatten(d[k], new, sep=sep).items())
            else:
                items.append((sep + new, d[k]))
        return dict(items)

    def _unflatten(self, d, sep='/'):
        """Converts a "flattened" dict i.e. {"full/path": "value", ...} into a nested dict structure"""
        output = {}
        for k in d:
            add(
                obj=output,
                path=k,
                value=d[k],
                sep=sep,
            )
        return output

    def merge(self):
        """Generate a merge of the local and remote dicts, following configurations set during __init__"""
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


def add(obj, path, value, sep='/'):
    """Add value to the `obj` dict at the specified path"""
    parts = path.strip(sep).split(sep)
    last = len(parts) - 1
    for index, part in enumerate(parts):
        if index == last:
            obj[part] = value
        else:
            obj = obj.setdefault(part, {})


def search(state, path):
    result = state
    for p in path.strip("/").split("/"):
        if result.clone(p):
            result = result[p]
        else:
            result = {}
            break
    output = {}
    add(output, path, result)
    return output


def merge(a, b):
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k in b:
        if k in result and isinstance(result[k], dict):
            result[k] = merge(result[k], b[k])
        else:
            result[k] = deepcopy(b[k])
    return result
