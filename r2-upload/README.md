# r2 upload

Uploads files to a Cloudflare R2 bucket with a pinned wrangler.

Every release pipeline ends by pushing artifacts to R2, and each one had grown its own copy of
`npm install -g wrangler` followed by a `wrangler r2 object put` loop. None of them pinned wrangler, so every
release picked up whatever version npm served that day — including across majors.

## Usage

```yaml
jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v8
        with:
          path: artifacts
          merge-multiple: true
      - uses: rewire-run/actions/r2-upload@v1
        with:
          bucket: rewire-releases
          files: artifacts/*.tar.gz
          api-token: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          account-id: ${{ vars.CLOUDFLARE_ACCOUNT_ID }}
```

`files` accepts globs and literal paths, space- or newline-separated:

```yaml
    files: |
      version.txt
      scripts/install.sh
      artifacts/*.tar.gz
```

## Keys and prefixes

By default each object is keyed by its basename, so `artifacts/rewire-1.0.0.tar.gz` becomes
`rewire-releases/rewire-1.0.0.tar.gz`.

Set `flatten: "false"` to keep the path instead, relative to `working-directory`. That is what a directory tree
such as an APT repository needs:

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

`prefix` is prepended verbatim, so include the trailing slash if you want one.

## Content types and caching

Each call applies one `content-type` and one `cache-control` to everything it uploads. A tree with several
classes of file — immutable packages alongside no-cache metadata — is therefore several calls rather than one:

```yaml
- uses: rewire-run/actions/r2-upload@v1     # immutable
  with:
    bucket: rewire-apt
    files: pool/main/*.deb
    cache-control: max-age=31536000
    # …

- uses: rewire-run/actions/r2-upload@v1     # regenerated every publish
  with:
    bucket: rewire-apt
    files: dists/stable/Release
    content-type: text/plain
    cache-control: "no-cache, max-age=300"
    # …
```

Leave `content-type` unset to infer it from the extension: `.wasm`, `.js`/`.mjs`, `.html`, `.css`, `.json`,
`.gz`/`.tgz`, `.deb`, `.asc`/`.gpg`, `.txt`/`.sh`. Anything unrecognized uploads without the flag so wrangler
applies its own default rather than a wrong guess — set it explicitly for extensionless files.

## Inputs

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

## Outputs

None.

## How it works

- Installs `wrangler@<wrangler-version>` — a pinned major by default, rather than whatever npm serves today.
- Expands `files` relative to `working-directory` and uploads each match with `wrangler r2 object put --remote`.
- Applies `--content-type` and `--cache-control` when set or inferred.

## Failure modes it makes loud

An upload step that quietly uploads nothing still reports success, and the broken release is only discovered by a
user. So this action **fails when a glob matches nothing**, and **fails when a literal path does not exist**.
Directories matched by a glob are skipped rather than treated as errors.
