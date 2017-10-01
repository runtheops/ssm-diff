from __future__ import print_function
from helpers import flatten, merge
import sys
import os
import yaml
import boto3
import dpath
import ast


class SecureTag(yaml.YAMLObject):
    yaml_tag = u'!secure'

    def __init__(self, secure):
        self.secure = secure

    def __repr__(self):
        return self.secure

    def __str__(self):
        return self.secure

    def __eq__(self, other):
        return self.secure == other.secure if isinstance(other, SecureTag) else False

    def __hash__(self):
        return hash(self.secure)

    def __ne__(self, other):
        return (not self.__eq__(other))

    @classmethod
    def from_yaml(cls, loader, node):
        return SecureTag(node.value)

    @classmethod
    def to_yaml(cls, dumper, data):
        return dumper.represent_scalar(cls.yaml_tag, data.secure)

yaml.SafeLoader.add_constructor('!secure', SecureTag.from_yaml)
yaml.SafeDumper.add_multi_representer(SecureTag, SecureTag.to_yaml)


class LocalState(object):
    def __init__(self, filename):
        self.filename = filename

    def get(self, paths, flat=True):
        try:
            output = {}
            with open(self.filename,'rb') as f:
                l = yaml.safe_load(f.read())
            for path in paths:
                if path.strip('/'):
                    output = merge(output, dpath.util.search(l, path))
                else:
                    return flatten(l) if flat else l
            return flatten(output) if flat else output
        except ValueError as e:
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

    def get(self, paths, flat=True):
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
                    value=self._read_param(param['Value'], param['Type'])
                )

        return flatten(output) if flat else output

    def _read_param(self, value, ssm_type='String'):
        try:
            output = ast.literal_eval(value)
        except Exception as e:
            output = value
        return SecureTag(output) if ssm_type == 'SecureString' else output

    def apply(self, diff):

        for k in diff.added():
            ssm_type = 'String'
            if isinstance(diff.target[k], list):
                ssm_type = 'StringList'
            if isinstance(diff.target[k], SecureTag):
                ssm_type = 'SecureString'
            self.ssm.put_parameter(
                Name=k,
                Value=str(diff.target[k]),
                Type=ssm_type
            )

        for k in diff.removed():
            self.ssm.delete_parameter(Name=k)

        for k in diff.changed():
            ssm_type = 'SecureString' if isinstance(diff.target[k], SecureTag) else 'String'

            self.ssm.put_parameter(
                Name=k,
                Value=str(diff.target[k]),
                Overwrite=True,
                Type=ssm_type
            )
