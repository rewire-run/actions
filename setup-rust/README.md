# setup rust

Installs a Rust toolchain, authenticates private git dependencies, and restores the cargo cache — the three
steps that open nearly every Rust job in this organization.

The reason to bundle them rather than call each by hand is **ordering**. The three steps are not independent:

1. The toolchain must exist first.
2. Credentials for private dependencies must be configured before anything resolves the dependency graph.
3. `Swatinem/rust-cache` hashes the lockfile, so it cannot run until private dependencies are reachable.

Getting that wrong does not fail loudly — it surfaces as a confusing `failed to authenticate when downloading
repository`, or as a cache that silently never hits. This action fixes the order once.

## Usage

```yaml
name: ci

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: rewire-run/actions/setup-rust@v1
        with:
          components: clippy
      - run: cargo clippy --all-features --all-targets -- -D warnings
```

## Private dependencies

Name every private repository in the dependency graph, including transitive ones:

```yaml
- uses: rewire-run/actions/setup-rust@v1
  with:
    private-repositories: iris, rustdds
    app-id: ${{ secrets.APP_ID }}
    private-key: ${{ secrets.APP_PRIVATE_KEY }}
```

Only jobs that resolve the dependency graph need this. `cargo fmt --check` parses source files and never touches
`Cargo.lock`, so a `fmt` job should omit `private-repositories` entirely rather than carry a credential it cannot
use. `clippy`, `test`, `doc`, and `build` all do need it.

## Cross-compiling and cache keys

Give each matrix leg its own cache key, or they overwrite each other:

```yaml
- uses: rewire-run/actions/setup-rust@v1
  with:
    targets: ${{ matrix.target }}
    cache-key: ${{ matrix.target }}
```

Use `cache-workspaces` when the repository checks out into a subdirectory rather than the workspace root:

```yaml
- uses: actions/checkout@v7
  with:
    path: rewire-bridge
- uses: rewire-run/actions/setup-rust@v1
  with:
    cache-workspaces: rewire-bridge
```

## Jobs that need no cache

`cargo fmt --check` has nothing worth caching:

```yaml
- uses: rewire-run/actions/setup-rust@v1
  with:
    components: rustfmt
    cache: "false"
```

## Inputs

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

## Outputs

None.

## How it works

- Installs the toolchain with `dtolnay/rust-toolchain@master`, passing `toolchain`, `components`, and `targets`.
  That action normally encodes the toolchain in its own ref (`@stable`, `@nightly`), so `@master` is its
  documented entry point when the toolchain is a parameter rather than a constant.
- When `private-repositories` is set, delegates to [`cargo-private-deps`](../cargo-private-deps) — see that
  action for how the token is minted and scoped.
- When `cache` is `true`, runs `Swatinem/rust-cache@v2` with `cache-key` and `cache-workspaces`.

## A note on the internal reference

This action calls `cargo-private-deps` by its full reference, `rewire-run/actions/cargo-private-deps@v1`, rather
than a relative path. Relative `uses: ./…` inside a composite action resolves against the **consumer's**
checked-out workspace, not this repository ([actions/runner#1348](https://github.com/actions/runner/issues/1348),
still open), so it would look for `cargo-private-deps/` inside whichever repo is running the workflow and fail.

The consequence to be aware of: when testing a change from a branch ref, `setup-rust@my-branch` still pulls
`cargo-private-deps@v1`, so a simultaneous change to both is not exercised end to end from the branch. Test such
a pair by temporarily pointing the internal reference at the branch, or land them in separate changes.

GitHub's `$/` self-repository syntax is the eventual fix — it resolves to the containing repository at the
running commit with no hardcoded ref — but its behavior inside a composite action consumed from another
repository is undocumented, and it does not exist on GitHub Enterprise Server. Revisit once that is settled.
