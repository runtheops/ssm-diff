from __future__ import print_function

import sys

import boto3
import termcolor
import yaml
from botocore.exceptions import ClientError, NoCredentialsError

from .helpers import merge, add, search


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
        return not self.__eq__(other)

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


class YAMLFile(object):
    """Encodes/decodes a dictionary to/from a YAML file"""
    def __init__(self, filename, paths=('/',)):
        self.filename = filename
        self.paths = paths

    def get(self):
        try:
            output = {}
            with open(self.filename, 'rb') as f:
                local = yaml.safe_load(f.read())
            for path in self.paths:
                if path.strip('/'):
                    output = merge(output, search(local, path))
                else:
                    return local
            return output
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


class ParameterStore(object):
    """Encodes/decodes a dict to/from the SSM Parameter Store"""
    def __init__(self, profile, diff_class, paths=('/',)):
        if profile:
            boto3.setup_default_session(profile_name=profile)
        self.ssm = boto3.client('ssm')
        self.diff_class = diff_class
        self.paths = paths

    def clone(self):
        p = self.ssm.get_paginator('get_parameters_by_path')
        output = {}
        for path in self.paths:
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

        return output

    # noinspection PyMethodMayBeStatic
    def _read_param(self, value, ssm_type='String'):
        return SecureTag(value) if ssm_type == 'SecureString' else str(value)

    def pull(self, local):
        diff = self.diff_class(
            remote=self.clone(),
            local=local,
        )
        return diff.merge()

    def dry_run(self, local):
        return self.diff_class(self.clone(), local).plan

    def push(self, local):
        plan = self.dry_run(local)

        # plan
        for k, v in plan['add'].items():
            # { key: new_value }
            ssm_type = 'String'
            if isinstance(v, list):
                ssm_type = 'StringList'
            if isinstance(v, SecureTag):
                ssm_type = 'SecureString'
            self.ssm.put_parameter(
                Name=k,
                Value=repr(v) if type(v) == SecureTag else str(v),
                Type=ssm_type)

        for k in plan['delete']:
            # { key: old_value }
            self.ssm.delete_parameter(Name=k)

        for k, delta in plan['change']:
            # { key: {'old': value, 'new': value} }
            v = delta['new']
            ssm_type = 'SecureString' if isinstance(v, SecureTag) else 'String'
            self.ssm.put_parameter(
                Name=k,
                Value=repr(v) if type(v) == SecureTag else str(v),
                Overwrite=True,
                Type=ssm_type)
