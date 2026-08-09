# build wasm

Builds a crate for `wasm32-unknown-unknown`, generates JS bindings with wasm-bindgen, and optionally optimizes
the module with `wasm-opt`.

## Usage

Install the toolchain first — this action assumes the `wasm32-unknown-unknown` target is already present:

```yaml
jobs:
  build-wasm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: rewire-run/actions/setup-rust@v1
        with:
          targets: wasm32-unknown-unknown
          cache-key: wasm32
      - uses: rewire-run/actions/build-wasm@v1
        with:
          crate-name: rewire_viewer
```

`crate-name` is the crate name **with underscores**, matching the `.wasm` file cargo produces — not the
hyphenated package name.

## Debug versus release

The default is a `debug` build, which is what a CI check wants. A release build that ships should also be
optimized:

```yaml
- uses: rewire-run/actions/build-wasm@v1
  with:
    crate-name: rewire_viewer
    profile: release
    optimize: "true"
```

`optimize` installs binaryen and rewrites the module in place with `wasm-opt -Oz`. It is off by default because
it adds a download and a pass that a pull-request check does not need.

## Output layout

Bindings and the module are written to `out-dir` (default `web/`):

```
web/<crate-name>.js
web/<crate-name>_bg.wasm
```

Upload them, or deploy them, from there:

```yaml
- uses: actions/upload-artifact@v7
  with:
    name: rewire-viewer-wasm
    path: |
      web/rewire_viewer.js
      web/rewire_viewer_bg.wasm
```

## Inputs

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

## Outputs

None.

## How it works

- Installs `wasm-bindgen-cli` at the pinned version, plus `llvm` and `clang`, which back the
  `AR_wasm32_unknown_unknown` and `CC_wasm32_unknown_unknown` variables the build needs.
- Builds `--lib` for `wasm32-unknown-unknown`.
- Runs `wasm-bindgen --target web` into `out-dir`.
- When `optimize` is set, installs binaryen and runs `wasm-opt -Oz` over the module.

Linux only — the LLVM install uses `apt-get`.

## Keep the wasm-bindgen version in step

`wasm-bindgen-version` must match the crate's `wasm-bindgen` dependency. A mismatch does **not** fail the build:
it produces bindings that fail at runtime, which is the worst kind of failure to debug. That is exactly why the
pin lives here rather than being repeated in every workflow that builds wasm.
