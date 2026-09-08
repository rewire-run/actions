# apt publish

Adds debs to the apt repository in R2 by editing its catalog in place.

An apt repository is a pool of `.deb` files plus a signed catalog listing them. A deb that is in the pool but not in
the catalog is invisible to `apt install`. This action downloads the current catalog from the bucket, replaces the
entries for the debs it is publishing, appends the rest untouched, re-signs the release, uploads, and then reads the
catalog back to check that every deb it published is listed.

Because nothing else in the catalog is touched, several repositories can publish into the same apt repository
without knowing about each other. The bridge publishes `rewire`, rewire-ros publishes `ros-<distro>-rewire-ros`, and
neither release removes the other's packages.

## Usage

```yaml
jobs:
  apt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v8
        with:
          pattern: deb-*
          merge-multiple: true
          path: debs
      - uses: rewire-run/actions/apt-publish@v1
        with:
          debs: debs/*.deb
          gpg-private-key: ${{ secrets.GPG_PRIVATE_KEY }}
          api-token: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          account-id: ${{ vars.CLOUDFLARE_ACCOUNT_ID }}
```

`debs` accepts globs and literal paths, space- or newline-separated, and fails when nothing matches.

## Architectures

Each architecture in `architectures` has its own index. A deb named `*_<arch>.deb` lands in that index only, and a
deb named `*_all.deb` lands in every index, which is how a launch-file-only package is installable on both amd64 and
arm64 from one file.

## Re-publishing

Publishing a deb whose filename is already in the catalog replaces its entry, so re-running a release is safe and a
rebuilt deb gets its new checksum instead of a duplicate line.

## Limits

- Two publishers running at the same moment race on the read-modify-write, and one loses its entries. Re-run the
  loser, which is idempotent.
- The catalog is never rebuilt from scratch, so a deb removed from the pool by hand stays listed until something
  publishes again.
- The catalog must already exist in the bucket. A failed read stops the publish rather than being treated as an
  empty catalog, because uploading an index with only the new debs would hide every package already published.
  Seed a new bucket with empty `Packages` objects by hand.

## Inputs

| Input              | Required | Default          | Description                                                   |
| ------------------ | -------- | ---------------- | ------------------------------------------------------------- |
| `debs`             | yes      | —                | Newline- or space-separated paths and globs. Fails if none match. |
| `bucket`           | no       | `rewire-apt`     | R2 bucket holding the repository.                             |
| `suite`            | no       | `stable`         | Suite under `dists/`.                                         |
| `component`        | no       | `main`           | Component under `pool/` and `dists/<suite>/`.                 |
| `architectures`    | no       | `amd64 arm64`    | Space-separated architectures whose indexes are maintained.   |
| `gpg-private-key`  | yes      | —                | Base64-encoded private key that signs the Release file.       |
| `gpg-uid`          | no       | `apt@rewire.run` | User ID of the signing key, also exported as the public key.  |
| `api-token`        | yes      | —                | Cloudflare API token with read and write access to the bucket. |
| `account-id`       | yes      | —                | Cloudflare account ID that owns the bucket.                   |
| `wrangler-version` | no       | `4`              | wrangler version to install.                                  |

## Outputs

None.

## How it works

- Installs `apt-utils`, `dpkg-dev` and a pinned wrangler, and imports the signing key.
- Fetches `dists/<suite>/<component>/binary-<arch>/Packages` for each architecture with `wrangler r2 object get`,
  not through the public hostname, which rejects GitHub's runners.
- Runs `dpkg-scanpackages` over the new debs only and merges the result into each index with `merge.py`, which
  keeps every existing stanza whose `Filename` is not being republished.
- Regenerates `Packages.gz`, `Release`, `Release.gpg` and `InRelease`, exports the public key, and uploads debs
  before indexes so the catalog never points at a file that is not there yet.
- Reads each index back from the bucket and fails if a published deb is not listed.

`merge.py --self-test` exercises the merge on an inline fixture.
