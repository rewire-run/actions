# validate tag

Fails the workflow unless the triggering tag matches the expected release format.

A release workflow triggered on `v*` also fires for `v1.2.3rc1`, `v1.2`, and anything else beginning with `v`.
This action is the gate that stops a malformed or wrong-kind tag from producing a release.

## Usage

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: rewire-run/actions/validate-tag@v1

  build:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      # …
```

Put it in its own job that everything else depends on, so no build work starts before the tag is accepted.

## Stable versus release candidates

`kind` selects the pattern:

| `kind`   | Pattern                       | Matches      | Rejects        |
| -------- | ----------------------------- | ------------ | -------------- |
| `stable` | `^v[0-9]+\.[0-9]+\.[0-9]+$`   | `v1.2.3`     | `v1.2.3rc1`    |
| `rc`     | `^v[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+$` | `v1.2.3rc1` | `v1.2.3`  |

The two are mutually exclusive by construction, so a stable release workflow gated on `kind: stable` will not
fire for a release candidate, and vice versa:

```yaml
- uses: rewire-run/actions/validate-tag@v1
  with:
    kind: rc
```

Note both reject `v1.2.3-rc1` — the hyphenated form is not the convention here.

## Custom patterns

`pattern` takes an ERE and overrides `kind` entirely:

```yaml
- uses: rewire-run/actions/validate-tag@v1
  with:
    pattern: '^release-[0-9]+$'
```

## Inputs

| Input     | Required | Default            | Description                                             |
| --------- | -------- | ------------------ | ------------------------------------------------------- |
| `kind`    | no       | `stable`           | `stable` for `vX.Y.Z`, `rc` for `vX.Y.ZrcN`.            |
| `pattern` | no       | —                  | Explicit ERE, overriding `kind`.                        |
| `tag`     | no       | `github.ref_name`  | Tag to validate.                                        |

## Outputs

None.

## How it works

Matches the tag against the pattern for `kind`, or against `pattern` when given, and exits non-zero with an
`::error::` annotation on a mismatch. An unrecognized `kind` is itself an error rather than a silent pass.
