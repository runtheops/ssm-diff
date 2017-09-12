from __future__ import print_function
from helpers import flatten
import sys
import os
import yaml
import boto3
import dpath
import json
import ast


class LocalState(object):
    def __init__(self, filename):
        self.filename = filename

    def get(self, flat=True):
        try:
            with open(self.filename,'rb') as f:
                l = yaml.load(f.read())

            return flatten(l) if flat else l
        except Exception as e:
            print(e, file=sys.stderr)
            if e.errno == 2:
                print("Please, run init before doing plan!")
            sys.exit(1)

    def save(self, state):
        try:
            with open(self.filename, 'wb') as f:
                f.write(yaml.safe_dump(
                    state,
                    default_flow_style=False)
                )
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)


class RemoteState(object):
    def __init__(self):
        self.ssm = boto3.client('ssm')

    def get(self, flat=True):
        paginator = self.ssm.get_paginator('describe_parameters')
        ssm_params = {
            "WithDecryption": True
        }

        r = {}

        for page in paginator.paginate():
            names = [ p['Name'] for p in page['Parameters'] ]
            for param in self.ssm.get_parameters(Names=names, **ssm_params)['Parameters']:
                dpath.util.new(r, param['Name'], self._read_param(param['Value']))

        return flatten(r) if flat else r

    def _read_param(self, value):
        try:
            return ast.literal_eval(value)
        except Exception as e:
            return value

    def apply(self, diff):
        ssm = self.ssm

        for k in diff.added():
            ssm.put_parameter(
                Name=k,
                Value=str(diff.target[k]),
                Type='String'
            )

        for k in diff.removed():
            ssm.delete_parameter(Name=k)

        for k in diff.changed():
            ssm.put_parameter(
                Name=k,
                Value=str(diff.target[k]),
                Overwrite=True,
                Type='String'
            )
