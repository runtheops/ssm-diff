# ssm-diff

AWS [SSM Parameter Store](https://aws.amazon.com/ec2/systems-manager/parameter-store) provides convenient, AWS-native, 
KMS-enabled storage for parameters and secrets.  The API makes it easy to request a branch (i.e. subtree) of parameters 
when you need to configure a machine, but AWS provides no human-friendly UI for bulk-managing a subtree.

`ssm-diff` enables bulk-editing of the SSM Parameter Store keys by converting the path-style values in the Parameter 
Store to and from YAML files, where they can be edited.  For example, the values at `/Dev/DBServer/MySQL/app1` and 
`/Dev/DBServer/MySQL/app2` will become: 

```
Dev:
  DBServer:
    MySQL:
      app1: <value>
      app2: <value>
```

While `ssm-diff` downloads the entire Parameter Store by default, CLI flags (contructor kwargs for programmatic users) 
make it possible to extract and work with specific branches, exclude encrypted (i.e. secret) keys, and/or download 
the encrypted version of secrets (e.g. for backup purposes). 

## WARNING:  MAKE A BACKUP AND ALWAYS `plan`
While this package allows you to apply operations to specific Parameter Store paths, this ability is innately dangerous.
You would not, for example, want to download a copy of a single path and then `push` that single path to the root, 
erasing everything outside of that path.  Parameter Store versions provide some protection from mistaken 
changes, but (to the best of our knowledge) **DELETES ARE IRREVERSIBLE**.

`ssm-diff` makes an effort to protect you against these kinds of mistakes:

- The `SSM_NO_DECRYPT` option can be used to create a local backup of your entire Parameter Store without storing
decrypted secrets locally.
- `paths` configurations are stored in environment variables -- and configured during `__init__` for programmatic users -- 
to help ensure stability between calls.
- YAML files include metadata that will attempt to prevent you from making calls in an incompatible path.  This data is 
stored in YAML keys like `ssm-diff:config` and **SHOULD NOT BE CHANGED OR REMOVED**.

Despite our efforts to protect you, **USE THIS PACKAGE AT YOUR OWN RISK** and **TAKE REASONABLE SAFETY PRECAUTIONS LIKE 
KEEPING A BACKUP COPY OF YOUR PARAMETER STORE**. 

## Installation
```
pip install ssm-diff
```

# Geting Started
This tool uses the native AWS SDK client `boto3` which provides a variety of [configuration options](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuration),
including environment variables and configuration files.  

## Authentication
Common authentication options include:

- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` (created in the IAM - Users - \<User\> - Security Credentials 
section)
- `AWS_SESSION_TOKEN` for temporary access keys ([CLI only](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_use-resources.html))
- call `aws configure` to create a local configuration file 
- If using a shared configuration, file, `AWS_PROFILE` determines which profile to use in a shared configuration file

If using an ENV-based authentication process, it may be necessary to set `AWS_DEFAULT_REGION` (e.g. `us-west-1`, `us-west-2`).

## Working with Parameters
To initialize the local YAML file, download it from Parameter Store using `clone`:
```
$ ssm-diff clone
```

The name of this file will depend on your settings (in priority order):

- if `-f` is set, the name provided
- if `SSM_ROOT_PATH` is used (see below) a filename derived from this path
- if  `AWS_PROFILE` is used, `<AWS_PROFILE>.yml`
- `parameters.yml` if no other condition is met

To update an existing file with changes from the Parameter Store, use `pull`:
```
$ ssm-diff pull
```
By default, this command will preserve local changes.  To overwrite local changes (keeping only added keys), use 
`--force`.

After editing the file (e.g. removing `/test/deep/key` and changing `test/dif/key1`), you cna preview the changes by 
running 'plan':
```
$ ssm-diff plan
-/test/deep/key
~/test/diff/key1:
        < old value
        > new value
```

When you're ready to actually update the SSM Parameter Store, run `push`:
```
$ ssm-diff push
```

NOTE:  The default `DiffResolver` does not cache the remote state so it cannot distinguish between a local add and 
remote delete.  Please use caution if keys are being removed (externally) from the Parameter Store as the `pull` 
command will not remove them from the local storage (even with `--force`) and the `push` command will restore them to 
the Parameter Store.

NOTE:  The default `DiffResolver` does not cache the remote state so it cannot recognize concurrent changes (i.e. where
both the local and remote value has changed).  Calling push will overwrite any remote changes (including any changes
made since the last `plan`).  

## Options
As discussed above (in the WARNING section). to help ensure the same configurations are preserved across commands, most 
configurations are managed using environment variables.  The following are available on all commands:

- `SSM_PATHS` limits operations to specific branches identified by these paths (separated by `;` or `:`).  For example, 
`clone` will only copy these branches, `pull` will only apply changes to local keys within these branches, and `push` 
will only apply changes to remote keys within these branches.
- `SSM_ROOT_PATH` determines the path that is used as the root of the YAML file.  For example, if `SSM_ROOT_PATH` is set
to `/app1/dev/server1`, the key `/app1/dev/server1/username` and `/app1/dev/server1/password` show up in the YAML as:
    ```
    username: <value>
    password: <value>
    ```
    As noted above, this will generate a file named `app1~dev~server1.yml` unless `-f` is used.  The root path must be 
    an ancestor of all paths in `SSM_PATHS` or an exception will be raised.
- `SSM_NO_SECURE` excludes encrypted keys from the backup and sync process (when set to `1` or case-insenistive `true`).
This helps ensure that secrets are not accessed unnecessarily and are not decrypted on local systems. 
- `SSM_NO_DECRYPT` does not decrypt `SecureString` values when they're downloaded. **NOTE:  This option should only be 
used to create a local backup without exposing secrets.**  The AWS CLI does not provide a way to directly upload 
already-encrypted values. If these values need to be restored, you will need to decrypt them using the KMS API and 
upload the decrypted values. Despite the complexity of a restore, this option ensures that you have a way to backup 
(and recover) your entire parameter store without downloading and storing unencrypted secrets.

## Examples
Let's assume we have the following parameters set in SSM Parameter Store:
```
/qa/ci/api/db_schema    = foo_ci
/qa/ci/api/db_user      = bar_ci
/qa/ci/api/db_password  = baz_ci (SecureString)
/qa/uat/api/db_schema   = foo_uat
/qa/uat/api/db_user     = bar_uat 
/qa/uat/api/db_password = baz_uat (SecureString)
```

`init` will create a `parameters.yml` file with the following contents:
```
ssm-diff:config:
  ssm-diff:root: /
  ssm-diff:paths:
  - /
  ssm-diff:no-secure: false
  ssm-diff:no-decrypt: false
qa:
  ci:
    api:
      db_schema: foo_ci
      db_user: bar_ci
      db_password: !Secret
        metadata:
          aws:kms:alias: alias/aws/ssm
          encrypted: false
        secret: 'baz_ci'
  uat:
    api:
      db_schema: foo_uat
      db_user: bar_uat
      db_password: !Secret
        metadata: 
          aws:kms:alias: alias/aws/ssm
          encrypted: true
        secret: 'baz_uat'
```

As you can see in this file:

- The environment settings during `init` are stored in the `ssm-diff:config` metadata section.  While
these are the default values, we strongly recommend that you do not edit (or remove0 this section. 
- KMS-encrypted (SecureString) are decrypted and identified by the `!Secret` YAML tag.  The `!Secret` tag supports
custom MKS aliases using the `aws:kms:alias` metadata key.  When adding secrets that use the default KMS key, you may 
use the simpler `!SecureString <decrypted value>` or the legacy `!secure <decrypted value>`.

Now we delete the entire `ci` tree and edit `uat` parameters (including changing the syntax for the secret:
```
ssm-diff:config:
  ssm-diff:root: /
  ssm-diff:paths:
  - /
  ssm-diff:no-secure: false
  ssm-diff:no-decrypt: false
qa:
  uat:
    api:
      db_schema: foo_uat
      db_charset: utf8mb4 
      db_user: bar_changed
      db_password: !SecureString 'baz_changed'
```

Running `plan` will give the following output:

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

Finally, `push` will run the AWS API calls needed to update the SSM Parameter Store itself to mirror the local changes.