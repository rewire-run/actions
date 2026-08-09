# cargo private deps

Lets `cargo` fetch git dependencies that live in private repositories of this organization.

`GITHUB_TOKEN` is scoped to the repository running the workflow, so it cannot read a sibling private repo — a
build that depends on one fails with `failed to authenticate when downloading repository`. This action mints a
short-lived installation token from the **Rewire CI** GitHub App, scoped to just the repositories you name, and
rewrites `https://github.com/<org>` git URLs to use it.

> Most Rust jobs should use [`setup-rust`](../setup-rust) instead, which wraps this action along with the
> toolchain and cache in the correct order. Reach for this one directly only when you need the credentials
> without the rest.

## Usage

Add it after the toolchain step and before anything that resolves the dependency graph — `cargo check`,
`clippy`, `test`, `doc`, `build`:

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

## Naming several repositories

Cargo must be able to fetch transitive git dependencies too, so name every private repository in the graph, not
just your direct dependency. Pass them comma- or newline-separated:

```yaml
    with:
      repositories: iris, rustdds
```

Public repositories do not belong in the list — the token is only needed for ones `GITHUB_TOKEN` cannot read.

## Inputs

| Input          | Required | Description                                                               |
| -------------- | -------- | ------------------------------------------------------------------------- |
| `repositories` | yes      | Private repos in this org that cargo must read, without the owner prefix. |
| `app-id`       | yes      | App ID of the Rewire CI GitHub App.                                       |
| `private-key`  | yes      | Private key (PEM) of the Rewire CI GitHub App.                            |

The organization is always the one running the workflow (`github.repository_owner`), so it is not an input.

## Outputs

None.

## How it works

- Mints an installation token scoped to `repositories` via `actions/create-github-app-token`.
- Sets `url.https://x-access-token:<token>@github.com/<org>.insteadOf https://github.com/<org>` in the global
  git config, so any cargo git dependency pointing at the org resolves with credentials.
- Exports `CARGO_NET_GIT_FETCH_WITH_CLI=true` so cargo fetches through the `git` CLI and honors that rewrite.

The token expires when the job ends and is scoped to the named repositories only. Note the rewrite is scoped to
`github.com/<org>` rather than all of `github.com`, so the token is never offered to third-party hosts.

## Prerequisites

Already configured for this organization, listed for whoever has to reproduce or rotate it:

1. The **Rewire CI** GitHub App exists, owned by the org, with **Repository permissions → Contents: Read-only**
   and no webhook.
2. It is installed on the org with access to the private dependency repositories.
3. Org secrets `APP_ID` and `APP_PRIVATE_KEY` hold its App ID and full PEM private key, and are available to the
   consuming repositories.

## Troubleshooting

A missing installation shows up as `404` on `/repos/<org>/<repo>/installation` rather than an auth error — the
App's credentials are fine, there is just no installation to mint a token from. The same 404 appears when a
repository is named in `repositories` but is not covered by the installation.
