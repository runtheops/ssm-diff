# ssm-diff

AWS [SSM Parameter Store](https://aws.amazon.com/ec2/systems-manager/parameter-store) is a really convenient, AWS-native, KMS-enabled storage for parameters and secrets. 

Unfortunately, as of now, it doesn't seem to provide any human-friendly ways of batch-managing [hierarchies of parameters](http://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-working.html#sysman-paramstore-su-organize).

The goal of the `ssm-diff` tool is to simplify that process by unwraping path-style
(/Dev/DBServer/MySQL/db-string13 = value) parameters into a YAML structure:
```
Dev:
  DBServer:
    MySQL:
      db-string13: value
```

Then, given that this local YAML representation of the SSM Parameter Store state was edited, `calculating and applying diffs` on the parameters. 

`ssm-diff` supports complex data types as values and can operate within single or multiple prefixes.

## Geting Started
Before we start editing the local representation of parameters state, we have to get it from SMM:
```
$ ssm-diff.py init
```

will create a local `parameters.yml` file that stores a YAML representation of the SSM Parameter Store state.

Once you accomplish editing this file, adding, modifying or deleting parameters, run:
```
$ ssm-diff.py plan
```

Which will show you the diff between this local representation and an SSM Parameter Store.

Finally
```
$ ssm-diff.py apply
```
will actually apply local changes to the Parameter Store.

Operations can also be limited to a particular prefix(es):

```
$ ssm-diff.py -p /dev -p /qa/ci {init,plan,apply}
```

## Examples
Let's assume we have the following parameters set in SSM Parameter Store:
```
/qa/ci/api/db_schema    = foo_ci
/qa/ci/api/db_user      = bar_ci
/qa/ci/api/db_password  = baz_ci
/qa/uat/api/db_schema   = foo_uat
/qa/uat/api/db_user     = bar_uat
/qa/uat/api/db_password = baz_uat

```

```
$ ssm-diff.py init
```
will create a `parameters.yml` file with the following content:

```
qa:
  ci:
    api:
      db_schema: foo_ci
      db_user: bar_ci
      db_password: !secure 'baz_ci'
  uat:
    api:
      db_schema: foo_uat
      db_user: bar_uat
      db_password: !secure 'baz_uat'
```

KMS-encrypted (SecureString) and String type values are distunguished by `!secure` YAML tag.

Let's drop the `ci`-related stuff completely, and edit `uat` parameters a bit, ending up with the following `parameters.yml` file contents:
```
qa:
  uat:
    api:
      db_schema: foo_uat
      db_charset: utf8mb4 
      db_user: bar_changed
      db_password: !secure 'baz_changed'
```

Running
```
$ ssm-diff.py plan
```
will give the following output:

```
- /qa/ci/api/db_schema
- /qa/ci/api/db_user
- /qa/ci/api/db_password
+ /qa/uat/api/db_charset = utf8mb4
~ /qa/uat/api/db_user:
  < bar_uat
  ---
  > bar_changed
~ /qa/uat/api/db_password:
  < baz_uat
  ---
  > baz_changed

```

Finally
```
$ ssm-diff.py apply
```
will actually do all the necessary modifications of parameters in SSM Parameter Store itself, applying local changes

## Known issues and limitations
- There's currently no option to use different KMS keys for `SecureString` values encryption.
