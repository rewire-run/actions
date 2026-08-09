# cargo build artifact

Builds a release binary — natively or cross-compiled with `cargo-zigbuild` — and packages it as a tarball named
`<archive-name>-<version>-<label>.tar.gz`.

## Usage

```yaml
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - target: x86_64-unknown-linux-gnu
            os: ubuntu-latest
            zigbuild: true
          - target: aarch64-apple-darwin
            os: macos-latest
            zigbuild: false
    steps:
      - uses: actions/checkout@v7
      - uses: rewire-run/actions/setup-rust@v1
        with:
          targets: ${{ matrix.target }}
          cache-key: ${{ matrix.target }}
      - uses: rewire-run/actions/cargo-build-artifact@v1
        id: build
        with:
          archive-name: rewire-viewer
          binaries: rewire-viewer
          target: ${{ matrix.target }}
          zigbuild: ${{ matrix.zigbuild }}
      - uses: actions/upload-artifact@v7
        with:
          name: rewire-viewer-${{ matrix.target }}
          path: ${{ steps.build.outputs.archive }}
```

Uploading is left to the caller, because artifact names and retention differ per repository.

## Cross-compiling

Set `zigbuild: true` to build through `cargo-zigbuild`, which installs Zig and targets a specific glibc. The
`glibc` input is appended to the target — `x86_64-unknown-linux-gnu` becomes `x86_64-unknown-linux-gnu.2.35` —
so the binary runs on distributions older than the runner.

zigbuild requires a `target`; the action fails if you enable it without one.

## Native builds

Leave `target` empty to build for the runner itself. Artifacts then come from `target/release` rather than
`target/<triple>/release`, and you must supply `label` explicitly, since there is no triple to name the archive
with:

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

## Bundling extra files

`extra-files` stages additional paths alongside the built binaries — for instance a binary downloaded from
another repository's release earlier in the job:

```yaml
- uses: rewire-run/actions/cargo-build-artifact@v1
  with:
    archive-name: rewire
    binaries: rewire
    target: ${{ matrix.target }}
    zigbuild: true
    cargo-args: -p cli
    extra-files: ../viewer-artifact/rewire-viewer
    working-directory: rewire-bridge
```

## Inputs

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

## Outputs

| Output    | Description                                        |
| --------- | -------------------------------------------------- |
| `archive` | Archive filename, relative to `working-directory`. |

`ARCHIVE` is also exported to `$GITHUB_ENV` for callers that already read it, but prefer the output.

## How it works

- Installs `cargo-zigbuild` and Zig when `zigbuild` is enabled.
- Builds `--release`, appending `.<glibc>` to the target under zigbuild.
- Stages `binaries` from `target/<triple>/release` — or `target/release` for a native build — plus any
  `extra-files`, then tars the staging directory.

Set cross-compilation environment such as `PKG_CONFIG_ALLOW_CROSS` at the job level; composite action steps
inherit it.

## Three things that fail loudly

- A **missing binary** fails the job.
- A **missing `extra-files` entry** fails the job. The pattern this replaces used `cp … 2>/dev/null || true` for
  a bundled binary, so a failed download shipped a release without it and still reported success.
- A **native build with no `label`** fails rather than producing an archive with an empty platform suffix.
