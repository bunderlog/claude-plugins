# A Release is made by `mise run release` and published by CI from its tag

Date: 2026-10-01

The marketplace installs `baloo` from this repo's `main`, and an installed copy updates only to a
new version, so a change to `plugins/baloo/`, or to the binary's source in `src/baloo/`, reaches
users only with a Release; their tests and `schema.json`, which editors read from `main`, need none.
`mise run release` makes one from the commits since the last `v*` tag that change what needs a
Release, so a commit only to the release tool, a test or the schema is never in a Release's
version or notes. The commits follow Conventional Commits: below 1.0 a breaking change or a `feat`
raises the minor, anything else the patch; from 1.0 a breaking change raises the major. It builds
that version for every platform, so a version that doesn't build is never tagged, then writes it
to `plugin.json` and to the line the README's CI recipe pins (ADR checks), and a section to
`CHANGELOG.md`, commits them as `chore(release): <version>` and tags the commit `v<version>`,
signed, for `git push --follow-tags`. The tag starts the Release workflow, which builds the
binaries for every platform and publishes them, their `SHA256SUMS` and the CHANGELOG section as
the GitHub Release (ADR binary).

The release tool is a Go module of its own, `src/release/`, outside the plugin and the binary's
module, so a change to it needs no Release; it takes the plugin's names from `src/baloo/names`.

## Considered options

- Bumping `version` by hand — easy to forget, and then the change reaches nobody.
- A CHANGELOG written by hand — better prose, but a chore on every Release, when the commits
  already say what changed.
- The release tool in the binary's module (until 2026-09-30) — one `go.mod` for both, so a
  dependency only the tool needed could change the binary users get, and what a Release ships was
  a list of folders to leave out.
- Counting every commit since the last tag (until 2026-09-30) — a `fix` to the release tool
  showed in the users' notes, and a `feat` to it raised the plugin's minor.
- A pre-push check that a push changing the plugin carries a Release — a Release is made when
  someone decides to make one, not with every push.
- A placeholder for the version in the README's CI recipe — nothing to keep up, but the recipe
  no longer runs as copied.
- A test failing when the README's version lags `plugin.json` — nothing forgotten, but an edit by
  hand at every Release.
- CI making the Release on every push to `main` — no local step, but the release commit would be
  CI's, unsigned, and CI would push to `main`.

## Consequences

- The message of a commit that changes the plugin is release notes: its subject is what users
  read. A commit that changes the plugin and something else counts whole.
- The release commit is signed like any other, and the tag always is (`git tag -s`), so the
  Release is made where the signing key is.
- Nothing stops a push that changes `plugins/baloo/` or `src/baloo/` without a Release: it
  reaches users with the next one.
