from __future__ import print_function
from helpers import flatten
import sys
import os
import yaml
import boto3
import dpath


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
        ssm = self.ssm
        resp = ssm.describe_parameters()

        getp = lambda r: ssm.get_parameters(
            Names=[ p['Name'] for p in r['Parameters'] ],
            WithDecryption=True
        )['Parameters']

        params = getp(resp)

        while resp.get('NextToken'):
            resp = ssm.describe_parameters(
                NextToken=resp['NextToken']
            )
            params.extend(getp(resp))

        r = {}
        for p in params:
            k, v = p['Name'], p['Value']
            dpath.util.new(r,k,v)

        return flatten(r) if flat else r

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
