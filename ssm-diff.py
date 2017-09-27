#!/usr/bin/env python
from states import *
import argparse
import os


def init(filename, paths, profile):
    r, l = RemoteState(profile), LocalState(filename)
    l.save(r.get(flat=False, paths=paths))


def apply(filename, paths, profile):
    r, _, diff = plan(filename, paths, profile)

    print "\nApplying changes..."
    try:
        r.apply(diff)
    except Exception as e:
        print "Failed to apply changes to remote:", e
    print "Done."


def plan(filename, paths, profile):
    r, l = RemoteState(profile), LocalState(filename)
    diff = helpers.FlatDictDiffer(r.get(paths=paths), l.get(paths=paths))

    if diff.differ:
        diff.print_state()
    else:
        print "Remote state it up to date."

    return r, l, diff


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='local state yml file', action='store', dest='filename', default='parameters.yml')
    parser.add_argument('--path', '-p', action='append', help='filter SSM path')
    parser.add_argument('--profile', help='AWS profile name', action='store', dest='profile', default='default')
    subparsers = parser.add_subparsers(help='commands')

    parser_plan = subparsers.add_parser('plan', help='display changes between local and remote states')
    parser_plan.set_defaults(func=plan)

    parser_init = subparsers.add_parser('init', help='create or overwrite local state snapshot')
    parser_init.set_defaults(func=init)

    parser_apply = subparsers.add_parser('apply', help='apply diff to the remote state')
    parser_apply.set_defaults(func=apply)

    args = parser.parse_args()
    paths = args.path if args.path else ['/']

    if args.filename == 'parameters.yml':
        if args.profile == 'default':
            if 'AWS_PROFILE' in os.environ:
                args.filename = os.environ['AWS_PROFILE'] + '.yml'
        else:
            args.filename = args.profile + '.yml'
    args.func(filename=args.filename, paths=paths, profile=args.profile)
