# A Release is made by `mise run release` and published by CI from its tag

Date: 2026-09-29

The marketplace installs `baloo` from this repo's `main`, and an installed copy updates only to
a new version, so a change to `plugins/baloo/` reaches users only with a Release.
`mise run release` (`go run ./cmd/release`) makes one from the commits since the last `v*` tag,
which follow Conventional Commits: below 1.0 a breaking change or a `feat` raises the minor,
anything else the patch; from 1.0 a breaking change raises the major. It writes the version to
`plugin.json`, the sha256 of every build to `scripts/SHA256SUMS` (ADR binary) and a section to
`CHANGELOG.md`, commits them as `chore(release): <version>` and tags the commit `v<version>`,
annotated, for `git push --follow-tags`. The tag starts the Release workflow, which publishes the
builds and the CHANGELOG section as the GitHub Release.

The release tool is not part of the plugin: a change only to it, in `cmd/release` or
`internal/release`, needs no Release.

## Considered options

- Bumping `version` by hand — in `am` it was forgotten, and the change reached nobody.
- A CHANGELOG written by hand — better prose, but a chore on every Release, when the commits
  already say what changed.
- CI making the Release on every push to `main` — no local step, but the release commit would be
  CI's, unsigned, and CI would push to `main`.

## Consequences

- A commit message is release notes: its subject is what users read.
- The release commit and tag are signed like any other, so the Release is made where the
  signing key is.
- Nothing yet stops a push that changes `plugins/baloo/` without a Release; `am` had a pre-push
  check for it, which comes back with the Git hooks.
