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
    <img alt="Version" src="https://img.shields.io/badge/version-v1.1.0-green">
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
| [`r2-upload`](#r2-upload)                   | Upload files to a Cloudflare R2 bucket with a pinned wrangler.   |
| [`github-release`](#github-release)         | Generate a changelog and publish a release with its artifacts.   |
| [`cargo-build-artifact`](#cargo-build-artifact) | Build a release binary and package it as a tarball.          |
| [`validate-tag`](#validate-tag)             | Fail unless the triggering tag matches the release format.       |
| [`build-wasm`](#build-wasm)                 | Build for wasm32, generate JS bindings, optionally optimize.     |

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

## `r2-upload`

Uploads files to a Cloudflare R2 bucket.

Every release pipeline ends by pushing artifacts to R2, and each one had grown its own copy of
`npm install -g wrangler` followed by a `wrangler r2 object put` loop. None of them pinned wrangler, so every
release picked up whatever version npm served that day — including across majors.

### Usage

Release artifacts, keyed by basename:

```yaml
- uses: rewire-run/actions/r2-upload@v1
  with:
    bucket: rewire-releases
    files: |
      version.txt
      artifacts/*.tar.gz
    api-token: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    account-id: ${{ vars.CLOUDFLARE_ACCOUNT_ID }}
```

A directory tree that must keep its structure, such as an APT repository — note `flatten: "false"` and the
`working-directory` that the keys are relative to:

```yaml
- uses: rewire-run/actions/r2-upload@v1
  with:
    bucket: rewire-apt
    working-directory: repo
    files: pool/main/*.deb
    flatten: "false"
    cache-control: max-age=31536000
    api-token: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    account-id: ${{ vars.CLOUDFLARE_ACCOUNT_ID }}
```

Each call applies one `content-type` and one `cache-control` to everything it uploads, so a tree with several
classes of file — immutable packages, no-cache metadata — is several calls rather than one.

### Inputs

| Input               | Required | Default | Description                                                       |
| ------------------- | -------- | ------- | ----------------------------------------------------------------- |
| `bucket`            | yes      | —       | R2 bucket to upload into.                                          |
| `files`             | yes      | —       | Newline- or space-separated paths and globs. Fails if none match.  |
| `prefix`            | no       | —       | Key prefix, used verbatim — include the trailing slash.            |
| `content-type`      | no       | —       | Applied to every file in this call; inferred when empty.           |
| `cache-control`     | no       | —       | Applied to every file in this call.                                |
| `flatten`           | no       | `true`  | Key by basename; `false` keeps the path relative to the workdir.   |
| `working-directory` | no       | `.`     | Directory that `files` resolves from.                              |
| `wrangler-version`  | no       | `4`     | wrangler version to install.                                       |
| `api-token`         | yes      | —       | Cloudflare API token with write access.                            |
| `account-id`        | yes      | —       | Cloudflare account ID owning the bucket.                           |

### Outputs

None.

### What it does

- Installs `wrangler@<wrangler-version>` — a pinned major by default, rather than whatever npm serves.
- Expands `files` relative to `working-directory` and uploads each match with `wrangler r2 object put --remote`.
- Sets `--content-type` from the caller's value, or infers it from the extension: `.wasm`, `.js`/`.mjs`,
  `.html`, `.css`, `.json`, `.gz`/`.tgz`, `.deb`, `.asc`/`.gpg`, `.txt`/`.sh`. Anything unrecognized is uploaded
  without the flag so wrangler applies its own default instead of a wrong guess.
- Sets `--cache-control` when given.

### Failure modes it makes loud

An upload step that quietly uploads nothing still reports success, and the broken release is only discovered by a
user. So this action fails when a glob matches nothing, and fails when a literal path does not exist. Directories
matched by a glob are skipped rather than treated as errors.

## `github-release`

Generates a changelog with git-cliff and publishes a GitHub release with the run's artifacts.

### Usage

```yaml
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: rewire-run/actions/github-release@v1
        with:
          files: artifacts/*
```

A notes-only release, for a repository that builds no artifacts:

```yaml
      - uses: rewire-run/actions/github-release@v1
        with:
          download-artifacts: "false"
```

A release candidate:

```yaml
      - uses: rewire-run/actions/github-release@v1
        with:
          files: artifacts/*
          prerelease: "true"
```

### Inputs

| Input                | Required | Default          | Description                                            |
| -------------------- | -------- | ---------------- | ------------------------------------------------------ |
| `files`              | no       | —                | Assets to attach. Empty means a notes-only release.    |
| `name`               | no       | `github.ref_name`| Release title.                                          |
| `prerelease`         | no       | `false`          | Mark as a pre-release.                                  |
| `changelog-config`   | no       | `cliff.toml`     | git-cliff configuration path.                           |
| `checkout`           | no       | `true`           | Check out at full depth before generating the changelog.|
| `download-artifacts` | no       | `true`           | Download and merge the run's artifacts first.           |
| `artifact-path`      | no       | `artifacts`      | Directory artifacts are downloaded into.                |

### Outputs

None.

### What it does

- Checks out at `fetch-depth: 0`. This is not optional for a changelog: git-cliff walks history, and a shallow
  clone yields an empty changelog rather than an error.
- Downloads every artifact from the run with `merge-multiple: true` into `artifact-path`.
- Runs git-cliff with `--latest --strip header`.
- Publishes with `softprops/action-gh-release`, using the changelog as the body and `generate_release_notes:
  false` so GitHub's autogenerated notes do not compete with git-cliff's.

The calling job needs `permissions: contents: write`.

### Note on `download-artifacts`

`actions/download-artifact` fails when the run produced no artifacts, so a repository that publishes notes only
must set `download-artifacts: "false"`. The default is `true` because most release pipelines here do build
something.

## `cargo-build-artifact`

Builds a release binary — natively or cross-compiled with `cargo-zigbuild` — and packages it as a tarball.

### Usage

Cross-compiled, bundling a binary downloaded from another repository's release:

```yaml
- uses: rewire-run/actions/cargo-build-artifact@v1
  id: build
  with:
    archive-name: rewire
    binaries: rewire
    target: ${{ matrix.target }}
    zigbuild: ${{ matrix.zigbuild }}
    cargo-args: -p cli
    extra-files: ../viewer-artifact/rewire-viewer
    working-directory: rewire-bridge
- uses: actions/upload-artifact@v7
  with:
    name: rewire-${{ matrix.target }}
    path: rewire-bridge/${{ steps.build.outputs.archive }}
```

Built natively for the runner, with the platform named explicitly:

```yaml
- uses: rewire-run/actions/cargo-build-artifact@v1
  with:
    archive-name: iris
    binaries: |
      libiris.rlib
      libiris.d
    label: ${{ matrix.target }}
    version: ${{ github.ref_name }}
    cargo-args: --all-features
```

### Inputs

| Input               | Required | Default            | Description                                                  |
| ------------------- | -------- | ------------------ | ------------------------------------------------------------ |
| `archive-name`      | yes      | —                  | Archive basename.                                            |
| `binaries`          | yes      | —                  | Files taken from the release directory into the archive.     |
| `target`            | no       | —                  | Triple to cross-compile for. Empty builds natively.          |
| `label`             | no       | `target`           | Platform suffix in the archive name.                         |
| `version`           | no       | tag without `v`    | Version in the archive name.                                 |
| `zigbuild`          | no       | `false`            | Cross-compile with `cargo zigbuild`.                         |
| `glibc`             | no       | `2.35`             | glibc version appended to the target for zigbuild.           |
| `cargo-args`        | no       | —                  | Extra build arguments, e.g. `-p cli`, `--all-features`.      |
| `extra-files`       | no       | —                  | Additional files staged alongside `binaries`.                |
| `working-directory` | no       | `.`                | Directory containing the cargo workspace.                    |

### Outputs

| Output    | Description                                                    |
| --------- | -------------------------------------------------------------- |
| `archive` | Archive filename, relative to `working-directory`.             |

`ARCHIVE` is also exported to `$GITHUB_ENV` for callers that already read it, but prefer the output.

### What it does

- Installs `cargo-zigbuild` and Zig when `zigbuild` is enabled.
- Builds `--release`, appending `.<glibc>` to the target under zigbuild.
- Stages `binaries` from `target/<triple>/release` — or `target/release` for a native build — plus any
  `extra-files`, then tars the staging directory into `<archive-name>-<version>-<label>.tar.gz`.

### Two things that fail loudly

A missing binary or a missing `extra-files` entry fails the job. The pattern this replaces used
`cp … 2>/dev/null || true` for the bundled viewer binary, so a failed download produced a release that shipped
without it and still reported success. A native build with no `label` also fails rather than producing an archive
named with an empty platform suffix.

## `validate-tag`

Fails the workflow unless the triggering tag matches the expected release format.

### Usage

```yaml
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: rewire-run/actions/validate-tag@v1
        with:
          kind: rc
```

### Inputs

| Input     | Required | Default            | Description                                             |
| --------- | -------- | ------------------ | ------------------------------------------------------- |
| `kind`    | no       | `stable`           | `stable` for `vX.Y.Z`, `rc` for `vX.Y.ZrcN`.            |
| `pattern` | no       | —                  | Explicit ERE, overriding `kind`.                        |
| `tag`     | no       | `github.ref_name`  | Tag to validate.                                        |

### Outputs

None.

### What it does

Matches the tag against the pattern for `kind`, or against `pattern` when given, and exits non-zero with an
`::error::` annotation on a mismatch. `stable` and `rc` are mutually exclusive by construction, so a release
workflow gated on `stable` will not fire for a release candidate.

## `build-wasm`

Builds a crate for `wasm32-unknown-unknown`, generates JS bindings, and optionally optimizes the module.

Install the toolchain first — this action assumes the `wasm32-unknown-unknown` target is already present:

```yaml
- uses: rewire-run/actions/setup-rust@v1
  with:
    targets: wasm32-unknown-unknown
    cache-key: wasm32
- uses: rewire-run/actions/build-wasm@v1
  with:
    crate-name: rewire_viewer
    profile: release
    optimize: "true"
```

### Inputs

| Input                  | Required | Default                  | Description                                       |
| ---------------------- | -------- | ------------------------ | ------------------------------------------------- |
| `crate-name`           | yes      | —                        | Crate name with underscores, e.g. `rewire_viewer`.|
| `profile`              | no       | `debug`                  | `debug` or `release`.                             |
| `cargo-args`           | no       | `--no-default-features`  | Extra build arguments.                            |
| `out-dir`              | no       | `web/`                   | wasm-bindgen output directory.                    |
| `optimize`             | no       | `false`                  | Run `wasm-opt -Oz`; installs binaryen.            |
| `wasm-bindgen-version` | no       | `0.2.117`                | wasm-bindgen-cli version.                         |
| `binaryen-version`     | no       | `version_130`            | binaryen release used when optimizing.            |
| `working-directory`    | no       | `.`                      | Directory containing the crate.                   |

### Outputs

None.

### What it does

- Installs `wasm-bindgen-cli` at the pinned version, plus `llvm` and `clang`, which back the
  `AR_wasm32_unknown_unknown` and `CC_wasm32_unknown_unknown` variables the build needs.
- Builds `--lib` for `wasm32-unknown-unknown`.
- Runs `wasm-bindgen --target web` into `out-dir`.
- When `optimize` is set, installs binaryen and rewrites the module in place with `wasm-opt -Oz`.

### Keep the wasm-bindgen version in step

`wasm-bindgen-version` must match the crate's `wasm-bindgen` dependency. A mismatch does not fail the build — it
produces bindings that fail at runtime, which is why the pin lives here rather than being repeated per workflow.

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
