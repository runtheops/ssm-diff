from __future__ import print_function
from botocore.exceptions import ClientError, NoCredentialsError
from .helpers import flatten, merge, add, search
import sys
import os
import yaml
import boto3
import termcolor

def str_presenter(dumper, data):
    if len(data.splitlines()) == 1 and data[-1] == '\n':
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str', data, style='>')
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar(
            'tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar(
        'tag:yaml.org,2002:str', data.strip())

yaml.SafeDumper.add_representer(str, str_presenter)

class SecureTag(yaml.YAMLObject):
    yaml_tag = u'!secure'

    def __init__(self, secure):
        self.secure = secure

    def __repr__(self):
        return self.secure

    def __str__(self):
        return termcolor.colored(self.secure, 'magenta')

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
        if len(data.secure.splitlines()) > 1:
            return dumper.represent_scalar(cls.yaml_tag, data.secure, style='|')
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
                    output = merge(output, search(l, path))
                else:
                    return flatten(l) if flat else l
            return flatten(output) if flat else output
        except IOError as e:
            print(e, file=sys.stderr)
            if e.errno == 2:
                print("Please, run init before doing plan!")
            sys.exit(1)
        except TypeError as e:
            if 'object is not iterable' in e.args[0]:
                return dict()
            raise

    def save(self, state):
        try:
            with open(self.filename, 'wb') as f:
                content = yaml.safe_dump(state, default_flow_style=False)
                f.write(bytes(content.encode('utf-8')))
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)


class RemoteState(object):
    def __init__(self, profile):
        if profile:
            boto3.setup_default_session(profile_name=profile)
        self.ssm = boto3.client('ssm')

    def get(self, paths=['/'], flat=True):
        p = self.ssm.get_paginator('get_parameters_by_path')
        output = {}
        for path in paths:
            try:
                for page in p.paginate(
                    Path=path,
                    Recursive=True,
                    WithDecryption=True):
                    for param in page['Parameters']:
                        add(obj=output,
                            path=param['Name'],
                            value=self._read_param(param['Value'], param['Type']))
            except (ClientError, NoCredentialsError) as e:
                print("Failed to fetch parameters from SSM!", e, file=sys.stderr)

        return flatten(output) if flat else output

    def _read_param(self, value, ssm_type='String'):
        return SecureTag(value) if ssm_type == 'SecureString' else str(value)

    def apply(self, diff):

        for k in diff.added():
            ssm_type = 'String'
            if isinstance(diff.target[k], list):
                ssm_type = 'StringList'
            if isinstance(diff.target[k], SecureTag):
                ssm_type = 'SecureString'
            self.ssm.put_parameter(
                Name=k,
                Value=repr(diff.target[k]) if type(diff.target[k]) == SecureTag else str(diff.target[k]),
                Type=ssm_type)

        for k in diff.removed():
            self.ssm.delete_parameter(Name=k)

        for k in diff.changed():
            ssm_type = 'SecureString' if isinstance(diff.target[k], SecureTag) else 'String'

            self.ssm.put_parameter(
                Name=k,
                Value=repr(diff.target[k]) if type(diff.target[k]) == SecureTag else str(diff.target[k]),
                Overwrite=True,
                Type=ssm_type)
