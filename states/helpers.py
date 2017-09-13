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
            print colored("+", 'green'), "{} = {}".format(k, self.target[k])

        for k in self.removed():
            print colored("-", 'red'), k

        for k in self.changed():
            print colored("~", 'yellow'), "{}:\n\t< {}\n\t> {}".format(k, self.ref[k], self.target[k])


def flatten(d, pkey='', sep='/'):
    items = []
    for k, v in d.items():
        new = pkey + sep + k if pkey else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new, sep=sep).items())
        else:
            items.append((sep + new, v))
    return dict(items)


def merge(a, b):
    if not isinstance(b, dict):
        return b
    result = deepcopy(a)
    for k, v in b.iteritems():
        if k in result and isinstance(result[k], dict):
            result[k] = merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result
