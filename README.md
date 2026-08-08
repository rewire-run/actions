<h1 align="center">
  <a href="https://rewire.run/">
    <img alt="banner" src="https://github.com/user-attachments/assets/4859413d-89b2-424c-a378-8a15260de384">
  </a>
</h1>

<p align="center">
  <a href="https://github.com/rewire-run/actions/actions/workflows/ci.yaml">
    <img alt="CI" src="https://github.com/rewire-run/actions/actions/workflows/ci.yaml/badge.svg">
  </a>
  <a href="https://github.com/rewire-run/actions/tags">
    <img alt="Version" src="https://img.shields.io/badge/version-v1.0.0-green">
  </a>
  <a href="https://github.com/rewire-run/actions/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue">
  </a>
  <a href="https://pixi.sh">
    <img alt="Powered by" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json">
  </a>
</p>

# GitHub Actions for [rewire.run](https://rewire.run)

Shared composite actions for Rewire CI workflows.

## Actions

| Action                                      | Description                                                      |
| ------------------------------------------- | ---------------------------------------------------------------- |
| [`cargo-private-deps`](#cargo-private-deps) | Let cargo fetch git dependencies from private repos in this org. |
| [`setup-bun`](#setup-bun)                   | Install the pinned Bun toolchain and restore dependencies.       |
| [`setup-rust`](#setup-rust)                 | Install Rust, authenticate private deps, and restore the cache.  |

## `cargo-private-deps`

Lets `cargo` fetch git dependencies that live in private repositories of this organization.

`GITHUB_TOKEN` is scoped to the repository running the workflow, so it cannot read a sibling private repo — a
build that depends on one fails with `failed to authenticate when downloading repository`. This action mints a
short-lived installation token from the **Rewire CI** GitHub App, scoped to just the repositories you name, and
rewrites `https://github.com/<org>` git URLs to use it.

### Usage

Add it after the toolchain step and before anything that resolves the dependency graph (`cargo check`,
`clippy`, `test`, `doc`, `build`):

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: dtolnay/rust-toolchain@stable
  - uses: rewire-run/actions/cargo-private-deps@v1
    with:
      repositories: rustdds
      app-id: ${{ secrets.APP_ID }}
      private-key: ${{ secrets.APP_PRIVATE_KEY }}
  - uses: Swatinem/rust-cache@v2
  - run: cargo test --all-features
```

Pass several repositories as a comma- or newline-separated list:

```yaml
    with:
      repositories: rustdds, some-other-crate
```

### Inputs

| Input          | Required | Description                                                               |
| -------------- | -------- | ------------------------------------------------------------------------- |
| `repositories` | yes      | Private repos in this org that cargo must read, without the owner prefix. |
| `app-id`       | yes      | App ID of the Rewire CI GitHub App.                                       |
| `private-key`  | yes      | Private key (PEM) of the Rewire CI GitHub App.                            |

The organization is always the one running the workflow (`github.repository_owner`), so it is not an input.

### Outputs

None.

### What it does

- Mints an installation token scoped to `repositories` via `actions/create-github-app-token`.
- Sets `url.https://x-access-token:<token>@github.com/<org>.insteadOf https://github.com/<org>` in the global
  git config, so any cargo git dependency pointing at the org resolves with credentials.
- Exports `CARGO_NET_GIT_FETCH_WITH_CLI=true` so cargo fetches through the `git` CLI and honors that rewrite.

The token expires when the job ends and is scoped to the named repositories only.

### Prerequisites

Already configured for this organization, listed for whoever has to reproduce or rotate it:

1. The **Rewire CI** GitHub App exists, owned by the org, with **Repository permissions → Contents: Read-only**
   and no webhook.
2. It is installed on the org with access to the private dependency repositories.
3. Org secrets `APP_ID` and `APP_PRIVATE_KEY` hold its App ID and full PEM private key, and are available to the
   consuming repositories.

### Troubleshooting

A missing installation shows up as `404` on `/repos/<org>/<repo>/installation` rather than an auth error —
the App's credentials are fine, there is just no installation to mint a token from.

## `setup-bun`

Installs the organization's pinned Bun toolchain and restores dependencies from the lockfile.

Every job in every JavaScript repository begins with the same two steps — install Bun, then
`bun install --frozen-lockfile`. Keeping the version pin here means an upgrade is one edit rather than one per
job, and it stops repositories from silently floating on `bun-version: latest`, where an upstream release can
break CI with no change on our side.

### Usage

```yaml
steps:
  - uses: actions/checkout@v6
  - uses: rewire-run/actions/setup-bun@v1
  - run: bun run build
```

In a monorepo, install from the directory that owns the lockfile:

```yaml
    with:
      working-directory: apps/api
```

Skip the install when a job only needs the runtime — a lint pass over a directory, say, with nothing to resolve:

```yaml
    with:
      install: "false"
```

### Inputs

| Input               | Required | Default | Description                                                         |
| ------------------- | -------- | ------- | ------------------------------------------------------------------- |
| `bun-version`       | no       | `1.3.5` | Bun version to install. Leave unset — this is the org pin.          |
| `install`           | no       | `true`  | Run `bun install --frozen-lockfile`.                                |
| `working-directory` | no       | `.`     | Directory containing the lockfile that dependencies install from.   |

### Outputs

None.

### What it does

- Installs Bun via `oven-sh/setup-bun@v2` at the pinned version.
- Runs `bun install --frozen-lockfile` in `working-directory`, unless `install` is `false`.

`--frozen-lockfile` is not optional: it fails the job when `bun.lock` disagrees with `package.json` rather than
silently resolving something the lockfile never recorded. CI should never be the place a lockfile changes.

### Upgrading Bun

Change the `bun-version` default in [`setup-bun/action.yml`](setup-bun/action.yml), then move the `v1` tag. Every
consumer picks it up on its next run, so verify against one repository from a branch ref first — see
[Versioning](#versioning). Keep the pin in step with the `packageManager` field that consuming repositories
declare in their `package.json`; a mismatch means CI and local development resolve differently.

## `setup-rust`

Installs a Rust toolchain, authenticates private git dependencies, and restores the cargo cache — the three
steps that open nearly every Rust job in this organization.

The reason to bundle them rather than call each by hand is **ordering**. The three steps are not independent:

1. The toolchain must exist first.
2. Credentials for private dependencies must be configured before anything resolves the dependency graph.
3. `Swatinem/rust-cache` hashes the lockfile, so it cannot run until private dependencies are reachable.

Getting that wrong does not fail loudly — it fails as a confusing `failed to authenticate when downloading
repository` or a cache that silently never hits. This action fixes the order once.

### Usage

Public dependencies only:

```yaml
steps:
  - uses: actions/checkout@v6
  - uses: rewire-run/actions/setup-rust@v1
    with:
      components: clippy
  - run: cargo clippy --all-features --all-targets -- -D warnings
```

With private dependencies in this organization, and a matrix target keyed into the cache:

```yaml
steps:
  - uses: actions/checkout@v6
  - uses: rewire-run/actions/setup-rust@v1
    with:
      targets: ${{ matrix.target }}
      cache-key: ${{ matrix.target }}
      private-repositories: iris, rustdds
      app-id: ${{ secrets.APP_ID }}
      private-key: ${{ secrets.APP_PRIVATE_KEY }}
  - run: cargo build --release --target ${{ matrix.target }}
```

A formatting job needs neither credentials nor a cache — `cargo fmt --check` never resolves the dependency
graph:

```yaml
  - uses: rewire-run/actions/setup-rust@v1
    with:
      components: rustfmt
      cache: "false"
```

### Inputs

| Input                  | Required | Default  | Description                                                        |
| ---------------------- | -------- | -------- | ------------------------------------------------------------------ |
| `toolchain`            | no       | `stable` | Toolchain to install — `stable`, `nightly`, or a version.          |
| `components`           | no       | —        | Comma-separated rustup components, e.g. `rustfmt`, `clippy`.       |
| `targets`              | no       | —        | Comma-separated target triples.                                     |
| `cache`                | no       | `true`   | Restore and save the cargo cache.                                   |
| `cache-key`            | no       | —        | Extra key to separate caches that would otherwise collide.          |
| `cache-workspaces`     | no       | —        | Workspace dirs, for repos that check out into a subdirectory.       |
| `private-repositories` | no       | —        | Private org repos cargo must read. Empty means all deps are public. |
| `app-id`               | no       | —        | Rewire CI App ID. Required with `private-repositories`.             |
| `private-key`          | no       | —        | Rewire CI private key. Required with `private-repositories`.        |

### Outputs

None.

### What it does

- Installs the toolchain with `dtolnay/rust-toolchain@master`, passing `toolchain`, `components`, and `targets`.
  That action encodes the toolchain in its own ref (`@stable`, `@nightly`), so `@master` is its documented entry
  point when the toolchain is a parameter rather than a constant.
- When `private-repositories` is set, delegates to [`cargo-private-deps`](#cargo-private-deps) — see that section
  for how the token is minted and scoped.
- When `cache` is `true`, runs `Swatinem/rust-cache@v2` with `cache-key` and `cache-workspaces`.

### Which inputs a job actually needs

Only jobs that resolve the dependency graph need credentials. `cargo fmt --check` does not — it parses source
files and never touches `Cargo.lock` — so a `fmt` job should omit `private-repositories` entirely rather than
carry a credential it cannot use. `clippy`, `test`, `doc`, and `build` all do need it.

### A note on the internal reference

This action calls `cargo-private-deps` by its full reference, `rewire-run/actions/cargo-private-deps@v1`, rather
than a relative path. Relative `uses: ./…` inside a composite action resolves against the **consumer's**
checked-out workspace, not this repository ([actions/runner#1348](https://github.com/actions/runner/issues/1348),
still open), so it would look for `cargo-private-deps/` inside whichever repo is running the workflow and fail.

The consequence to be aware of: when testing a change from a branch ref, `setup-rust@my-branch` still pulls
`cargo-private-deps@v1`, so a simultaneous change to both is not exercised end to end from the branch. Test such
a pair by temporarily pointing the internal reference at the branch, or land them in separate changes.

GitHub's `$/` self-repository syntax is the eventual fix here — it resolves to the containing repository at the
running commit with no hardcoded ref — but its behavior inside a composite action consumed from another
repository is not documented, and it is unavailable on GitHub Enterprise Server. Revisit once that is settled.

## Development

Checks run through [pixi](https://pixi.sh):

```bash
pixi run sanity   # actionlint + schema — run before every commit
pixi run lint     # actionlint over the workflows
pixi run schema   # validate every action.yml against the GitHub Action schema
```

CI runs the same two checks on every push and PR — see [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml).

## Versioning

Reference the major tag, `@v1`. It moves forward across compatible changes; releases are also tagged with the
full `vX.Y.Z`. Avoid `@main` in release pipelines — it changes under you the moment this repo is pushed.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
