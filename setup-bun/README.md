# setup bun

Installs the organization's pinned Bun toolchain and restores dependencies from the lockfile.

Every job in every JavaScript repository begins with the same two steps — install Bun, then
`bun install --frozen-lockfile`. Keeping the version pin here means an upgrade is one edit rather than one per
job, and it stops repositories from silently floating on `bun-version: latest`, where an upstream release can
break CI with no change on our side.

## Usage

```yaml
name: ci

on:
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: rewire-run/actions/setup-bun@v1
      - run: bun run build
```

You should not normally pass any inputs — the defaults are the org convention.

## Monorepos

Install from the directory that owns the lockfile:

```yaml
- uses: rewire-run/actions/setup-bun@v1
  with:
    working-directory: apps/api
```

A workspace root that owns the single lockfile for all packages needs nothing special — the default installs
once at the root, which is what a Bun workspace expects.

## Skipping the install

Some jobs need the runtime but have nothing to resolve:

```yaml
- uses: rewire-run/actions/setup-bun@v1
  with:
    install: "false"
```

## Inputs

| Input               | Required | Default | Description                                                         |
| ------------------- | -------- | ------- | ------------------------------------------------------------------- |
| `bun-version`       | no       | `1.3.5` | Bun version to install. Leave unset — this is the org pin.          |
| `install`           | no       | `true`  | Run `bun install --frozen-lockfile`.                                |
| `working-directory` | no       | `.`     | Directory containing the lockfile that dependencies install from.   |

## Outputs

None.

## How it works

- Installs Bun via `oven-sh/setup-bun@v2` at the pinned version.
- Runs `bun install --frozen-lockfile` in `working-directory`, unless `install` is `false`.

`--frozen-lockfile` is not optional here: it fails the job when `bun.lock` disagrees with `package.json` rather
than silently resolving something the lockfile never recorded. CI should never be the place a lockfile changes.

## Upgrading Bun

Change the `bun-version` default in [`action.yml`](action.yml), then move the `v1` tag. Every consumer picks it
up on its next run, so verify against one repository from a branch ref first.

Keep the pin in step with the `packageManager` field that consuming repositories declare in their
`package.json`. A mismatch means CI and local development resolve different Bun versions, which produces
failures reproducible in only one of the two places.
