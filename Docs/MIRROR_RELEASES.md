# Mirroring releases from another repository

This repo can copy the GitHub Releases of an upstream project (titles, release
notes and binary assets) into itself, byte-for-byte.

It is used to mirror the ten AstroHybrid builds (`v1.0.0` – `v1.0.9`, ~1.67 GiB
of zips) from `imnotsharingmyname/pcportastrobot`. Because this repository is a
fork of that project, the tags already exist here and point at the same commits;
only the release objects and their assets need to be copied.

## How to run it

1. Actions → **Mirror releases** → *Run workflow* (on `main`), or:

   ```bash
   gh workflow run mirror-releases.yml --repo <owner>/<repo> --ref main \
     -f source_repo=imnotsharingmyname/pcportastrobot
   ```

2. With the default inputs it copies every upstream release, verifies each
   asset's size and sha256 against upstream, publishes the releases and marks
   the newest one *latest* (the launcher's update check reads that).

| Input | Effect |
| --- | --- |
| `tags` | Space/comma separated subset, e.g. `v1.0.8 v1.0.9`. Blank = all. |
| `draft` | Leave the copies as drafts instead of publishing. |
| `overwrite` | Re-create releases that already exist / re-upload assets. Published releases are otherwise left untouched, so re-runs are safe. |
| `skip_assets` | Metadata only (titles + notes), no binaries. |
| `dry_run` | Print the plan, change nothing. |

## Why it runs in Actions

Release assets are served from `release-assets.githubusercontent.com` and
uploaded to `uploads.github.com`. Those hosts are typically blocked from a
development sandbox, while a GitHub-hosted runner has normal network access.
`Tools/release/mirror_releases.sh` can also be run locally from any machine that
can reach both hosts (it needs `gh`, `curl`, `git`, `sha256sum`).

## Notes

- Assets are downloaded one at a time and deleted after upload, so peak disk use
  is roughly the largest single asset (~200 MB).
- Release notes are copied verbatim, including trailing newlines and CRLF.
- Copied releases keep the upstream tag targets; nothing is retagged and no
  history is rewritten.
