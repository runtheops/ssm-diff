from termcolor import colored
from copy import deepcopy
import collections


class FlatDictDiffer(object):
    def __init__(self, ref, target):
        self.ref, self.target = ref, target
        self.ref_set, self.target_set = set(ref.keys()), set(target.keys())
        self.isect = self.ref_set.intersection(self.target_set)

        if self.added() or self.removed() or self.changed():
            self.differ = True
        else:
            self.differ = False

    def added(self):
        return self.target_set - self.isect

    def removed(self):
        return self.ref_set - self.isect

    def changed(self):
        return set(k for k in self.isect if self.ref[k] != self.target[k])

    def unchanged(self):
        return set(k for k in self.isect if self.ref[k] == self.target[k])

    def print_state(self):
        for k in self.added():
            print(colored("+", 'green'), "{} = {}".format(k, self.target[k]))

        for k in self.removed():
            print(colored("-", 'red'), k)

        for k in self.changed():
            print(colored("~", 'yellow'), "{}:\n\t< {}\n\t> {}".format(k, self.ref[k], self.target[k]))


def flatten(d, pkey='', sep='/'):
    items = []
    for k in d:
        new = pkey + sep + k if pkey else k
        if isinstance(d[k], collections.MutableMapping):
            items.extend(flatten(d[k], new, sep=sep).items())
        else:
            items.append((sep + new, d[k]))
    return dict(items)


def add(obj, path, value):
    parts = path.strip("/").split("/")
    last = len(parts) - 1
    for index, part in enumerate(parts):
        if index == last:
            obj[part] = value
        else:
            obj = obj.setdefault(part, {})


def search(state, path):
    result = state
    for p in path.strip("/").split("/"):
        if result.get(p):
            result = result[p]
        else:
            result = {}
            break
    output = {}
    add(output, path, result)
    return output


def unflatten(d):
    output = {}
    for k in d:
        add(
            obj=output,
            path=k,
            value=d[k])
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
