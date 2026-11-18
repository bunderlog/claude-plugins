# A Release is made by `mise run release` and published by CI from its tag

Date: 2026-11-18

The marketplace installs its plugins from this repo's `main`, each from the folder
`.claude-plugin/marketplace.json` names, and an installed copy updates only to a new version, so a
change to a plugin's folder reaches users only with a Release, and the tests, in `tests/`, are
outside it. All the marketplace's plugins are released together, under one version (ADR plugin):
`mise run release` makes one Release from the commits since the last `v*` tag that change any
plugin's folder, so a commit only to the release tool or a test is never in a Release's version or
notes. The commits follow Conventional Commits: below 1.0 a breaking change or a `feat` raises the
minor, anything else the patch; from 1.0 a breaking change raises the major. It writes that version
to every plugin's `plugin.json`, which must all carry the same one before, and a section to
`CHANGELOG.md`, a part per plugin a commit changed where there are several; commits them as
`chore(release): <version>` and tags the commit `v<version>`, signed. Before it writes anything,
`main` must be the same here and on origin, and each workflow that runs on a push to `main` must
have passed on the newest commit it ran on, every later commit being one it ignores by its
`paths`; else the task stops and says what to wait for or fix, as a push to `main` is what users
install. The task then pushes `main` and the tag together; the tag starts the Release workflow, which publishes the CHANGELOG section as
the GitHub Release. With nothing to build or download (ADR binary), a copy that updates before the
workflow has run misses only the notes page.

The site, bunderlog/web, describes what ships, and on 2026-11-18 it fell three Releases behind
until the user noticed. So once a Release has a breaking change or a feature, the task prints
them with a reminder to update the site, for the session that made the Release to take up. A
Release of fixes alone prints nothing: a fix brings the code back to what the site already says.

The release tool, `src/release/release.py`, is Python like the plugins, outside them, and shares
no code with them: it reads the plugins from the marketplace's manifest, so a change to it needs no
Release.

## Considered options

- One plugin's Release, `plugins/baloo/` only (until 2026-11-10) — a second plugin couldn't ship.
- A tag per plugin, `<plugin>--v<version>`, which Claude Code resolves a plugin's `dependencies`
  against — no plugin depends on another yet; `v*` alone until one does.
- The version in the marketplace's entries too — a second place for it; each `plugin.json` holds
  it.
- Bumping `version` by hand — easy to forget, and then the change reaches nobody.
- A CHANGELOG written by hand — better prose, but a chore on every Release, when the commits
  already say what changed.
- The release tool in the binary's module (until 2026-09-30) — one `go.mod` for both, so a
  dependency only the tool needed could change the binary users get, and what a Release ships was
  a list of folders to leave out.
- Counting every commit since the last tag (until 2026-09-30) — a `fix` to the release tool
  showed in the users' notes, and a `feat` to it raised the plugin's minor.
- The Release workflow pushing an item to bunderlog/web's Inbox, or opening an issue there — the
  workflow's token writes to this repo alone, so it needs a key to another repo kept as a
  secret, for what the session making the Release can do itself.
- A pre-push check that a push changing the plugin carries a Release — a Release is made when
  someone decides to make one, not with every push.
- A commit after each Release pinning the README's recipe for running the commit Checks in CI to
  the tagged commit (until 2026-11-09) — the Checks moved to `hathi`, which CI runs from the
  version `mise.toml` pins (ADR git-hooks).
- The recipe pinning the tag (until 2026-10-14) — one commit a Release, but a moved tag would
  run other code in a project's CI.
- A placeholder for the version in the README's CI recipe — nothing to keep up, but the recipe
  no longer runs as copied.
- A test failing when the README's version lags `plugin.json` — nothing forgotten, but an edit by
  hand at every Release.
- The push left to whoever ran the task (until 2026-10-01) — a Release made and never pushed
  reaches nobody, and one sat local for three sessions until the next was pushed with it.
- Pushing `main` only once the Release workflow had published the binaries (until 2026-10-14) — no
  copy updated to a version whose binaries weren't there, at a minute's wait; with the code in the
  plugin, nothing is missing.
- Building the release for every platform before tagging (until 2026-10-14) — a version that
  didn't build was never tagged; Python has no build.
- Keeping the release tool in Go (until 2026-10-14) — it worked and never ships, but the repo
  would keep a Go toolchain for one tool.
- A Release as a tag and `CHANGELOG.md` alone, with no workflow — one less moving part, but no
  notes page on GitHub.
- No check before a Release (until 2026-11-18) — 0.69.0 went out with CI on macOS still running,
  and the CI the Release's own push started could only tell afterwards.
- The Release workflow waiting for CI on the tagged commit — but users install from `main`, which
  the push has already changed by then.
- CI making the Release on every push to `main` — no local step, but the release commit would be
  CI's, unsigned, and CI would push to `main`.

## Consequences

- CI skips a Release's own commit, which changes only the versions and the CHANGELOG of code it
  has just passed; a commit only to `.about/` or this repo's own Markdown runs no tests, and
  `src/release/release.py` reads each workflow's `paths` for its check, so the two can't disagree.
- A Release waits for CI: after a merge or a push, `mise run release` stops until the runs end.

- The message of a commit that changes the plugin is release notes: its subject is what users
  read, and a breaking change's `BREAKING CHANGE:` footer is printed under it, so the footer says
  what users must do. A commit that changes the plugin and something else counts whole.
- The release commit is signed like any other, and the tag always is (`git tag -s`), so the
  Release is made where the signing key is.
- If the Release workflow fails, users already have the version, only without its notes page;
  fix the workflow and rerun it.
- Nothing stops a push that changes `plugins/baloo/` without a Release: it reaches users with the
  next one.
- A pull request lands on `main` by rebase (`gh pr merge --rebase`), never squashed, so each of its
  commits keeps its own subject in the CHANGELOG. A fix to a feature its branch adds, before any
  Release carries it, is folded into that feature's commit, so the notes get one line for the
  feature and none for fixing it.
