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
    <img alt="Version" src="https://img.shields.io/badge/version-v1.2.0-green">
  </a>
  <a href="https://github.com/rewire-run/actions/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue">
  </a>
  <a href="https://pixi.sh">
    <img alt="Powered by" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json">
  </a>
</p>

# GitHub Actions for [rewire.run](https://rewire.run)

Shared composite actions for Rewire CI workflows, so that a toolchain pin, a credential rotation, or a
dependency bump is one edit here rather than one per job across every repository.

Each action lives in its own directory with its own README. Reference them by the major tag:

```yaml
steps:
  - uses: actions/checkout@v6
  - uses: rewire-run/actions/setup-rust@v1
    with:
      components: clippy
  - run: cargo clippy --all-features --all-targets -- -D warnings
```

## Actions

### Toolchains

| Action | Description |
| ------ | ----------- |
| [`setup-bun`](setup-bun) | Install the pinned Bun toolchain and restore dependencies from the lockfile. |
| [`setup-rust`](setup-rust) | Install Rust, authenticate private git dependencies, and restore the cargo cache. |
| [`cargo-private-deps`](cargo-private-deps) | Let cargo fetch git dependencies from private repositories in this org. |

### Releases

| Action | Description |
| ------ | ----------- |
| [`validate-tag`](validate-tag) | Fail unless the triggering tag matches the expected release format. |
| [`cargo-build-artifact`](cargo-build-artifact) | Build a release binary, natively or cross-compiled, and package it. |
| [`build-wasm`](build-wasm) | Build for wasm32, generate JS bindings, and optionally optimize. |
| [`github-release`](github-release) | Generate a changelog with git-cliff and publish a GitHub release. |
| [`r2-upload`](r2-upload) | Upload files to a Cloudflare R2 bucket with a pinned wrangler. |

## Versioning

Reference the major tag, `@v1`. It moves forward across compatible changes; releases are also tagged with the
full `vX.Y.Z`. Avoid `@main` in release pipelines — it changes under you the moment this repo is pushed.

Because every consumer pins `@v1`, moving that tag deploys to the whole organization at once. Test a change from
a branch ref in one repository first, and never move `v1` in the same change that authors it.

## Development

Checks run through [pixi](https://pixi.sh):

```bash
pixi run sanity   # actionlint + schema — run before every commit
pixi run lint     # actionlint over every action and workflow
pixi run schema   # validate every action.yml against the GitHub Action schema
```

CI runs the same two checks on every push and PR — see [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml).

New actions go in their own top-level directory with an `action.yml` and a `README.md` following the shape of
the existing ones: what it does, usage, topic sections, inputs, outputs.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
