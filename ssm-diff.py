#!/usr/bin/env python
from states import *
import argparse


def init(filename):
    r, l = RemoteState(), LocalState(filename)
    l.save(r.get(flat=False))


def apply(filename):
    r, _, diff = plan(filename)

    print "\nApplying changes..."
    try:
        r.apply(diff)
    except Exception as e:
        print "Failed to apply changes to remote:", e
    print "Done."


def plan(filename):
    r, l = RemoteState(), LocalState(filename)
    diff = helpers.FlatDictDiffer(r.get(),l.get())

    if diff.differ:
        diff.print_state()
    else:
        print "Remote state it up to date."
    
    return r, l, diff


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='local state yml file', action='store', dest='filename', nargs=1, default='parameters.yml')
    subparsers = parser.add_subparsers(help='commands')

    parser_init = subparsers.add_parser('plan', help='display changes between local and remote states')
    parser_init.set_defaults(func=plan)

    parser_init = subparsers.add_parser('init', help='create or overwrite local state snapshot')
    parser_init.set_defaults(func=init)

    parser_apply = subparsers.add_parser('apply', help='apply diff to the remote state')
    parser_apply.set_defaults(func=apply)

    args = parser.parse_args()

    args.func(filename=args.filename)
