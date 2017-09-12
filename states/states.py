from __future__ import print_function
from helpers import flatten, merge
import sys
import os
import yaml
import boto3
import dpath
import ast


class LocalState(object):
    def __init__(self, filename):
        self.filename = filename

    def get(self, flat=True, paths=['/']):
        try:
            output = {}
            with open(self.filename,'rb') as f:
                l = yaml.load(f.read())
            for path in paths:
                output = merge(output, dpath.util.search(l, path))
            return flatten(output) if flat else output
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

    def get(self, flat=True, paths=['/']):
        paginator = self.ssm.get_paginator('describe_parameters')
        ssm_params = {
            "WithDecryption": True
        }
        ssm_describe_params = {
            'ParameterFilters': [
                {
                    'Key': 'Path',
                    'Option': 'Recursive',
                    'Values': paths
                }
            ]
        }

        output = {}

        for page in paginator.paginate(**ssm_describe_params):
            names = [ p['Name'] for p in page['Parameters'] ]
            for param in self.ssm.get_parameters(Names=names, **ssm_params)['Parameters']:
                dpath.util.new(
                    obj=output,
                    path=param['Name'],
                    value=self._read_param(param['Value'])
                )

        return flatten(output) if flat else output

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
