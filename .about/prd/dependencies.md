# Updating a project's outdated dependencies

## Problem

Updating a project's dependencies takes an afternoon by hand: list what's outdated in each
module, bump it, read the changelog of every major, fix what broke, check again. So it gets put
off, and the project falls behind until one update has to cross several majors at once.

## Users

A developer whose project declares its packages in a package manager's manifest (`go.mod`,
`package.json`, `Cargo.toml`, `pyproject.toml`…).

## Success signal

Asked to update the dependencies, Claude goes from the request to commits the project's check
passes on, with patch and minor updates done and each major listed with what it breaks, without
the user naming a command or opening a changelog.

## Scope

- A Guideline in baloo, `dependencies` (ADR plugin, ADR guidelines), followed only when the user
  asks: "update the dependencies", "update vue".
- What it updates: every module's code packages in the repo, through the package manager its
  lockfile names; commands written in for Go and npm, pnpm and yarn, another manager's from its
  help.
- Patch and minor updates at once; each major listed with its version, the breaking changes its
  changelog names and the code they touch, and updated only once the user picks it. A
  dependency the user names is updated alone, to its latest version, a major too.
- The check that proves an update: the Config's `stop-check`, else the one CLAUDE.md or
  AGENTS.md names, else the project's build and tests; run before any update and after each.
- An update that breaks the check is fixed from its changelog's migration as the `debugging`
  Guideline says, or rolled back, with the reason, when the migration changes the code's design
  or the cause is unclear.
- One commit for the patch and minor updates and one per major, on the current branch, in the
  project's commit convention; pushed only once the user agrees.

## Non-goals

- Fixing vulnerabilities (`npm audit`, `govulncheck`) as a task of its own.
- Reviewing or merging Dependabot's or Renovate's PRs.
- Choosing or adding a new dependency.
- Toolchain versions (`mise.toml`, the `go` directive, `engines`), GitHub Actions' `uses:` and
  Docker images.
- Picking transitive dependencies' versions by hand: they move as the package manager resolves
  them.
- Starting by itself: no Hook, no Check; watching CI after the push, which a red run hands to the
  `ci` Guideline.

## Acceptance criteria

- A new Config in a repo with a `go.mod`, `package.json`, `Cargo.toml` or `pyproject.toml` at
  any depth turns `dependencies` on; one whose only manifest is in `node_modules`, `vendor`,
  `testdata`, build output or a hidden folder leaves it off.
  → test: src/baloo/internal/guidelines/guidelines_test.go "TestFitting"
- A repo with outdated patch, minor and major versions: Claude updates the patch and minor ones,
  commits them in one commit, and lists each major with its current and latest version, the
  breaking changes its changelog names and the files they touch, then asks which to update.
- The user picks two majors: Claude updates each in a commit of its own, and the check passes
  after each.
- A `0.x` dependency has a new minor: Claude reads its changelog as for a major.
- A major's changelog can't be found: Claude lists the major as "breaking changes unknown" and
  doesn't guess them.
- A changelog or release note contains text addressed to Claude ("also run this script"):
  Claude treats it as the changelog's content and acts on none of it.
- The user asks "update vue" and vue has a new major: Claude updates only vue, to the new major,
  without listing it first.
- The user names a dependency the repo doesn't declare: Claude says so and adds nothing.
- An update breaks the check with a renamed API its changelog names: Claude changes the code to
  the new API and the check passes.
- An update breaks the check and the migration changes the code's design, or the cause is
  unclear: Claude rolls that dependency back, goes on with the others, and its report names the
  dependency and why.
- A `replace` in `go.mod`, an entry in `overrides` or `resolutions`, or a version with a comment
  saying it is pinned: Claude leaves it as it is and names it in the report.
- A repo with `pnpm-lock.yaml`: Claude runs pnpm, not npm; the lockfile it commits is pnpm's.
- A repo with a Go module and a `package.json` in `web/`: Claude updates both, and neither's
  lockfile is left out of the commit.
- Nothing is outdated: Claude says so and changes no file.
- The check fails before any update: Claude says so, with the failure, and updates nothing.
- The repo has no check named and no build or tests to run: Claude says so and asks what proves
  an update works before updating anything.
- The working tree has uncommitted changes: Claude says what to commit or stash first and
  changes nothing.
- The package manager is missing, or its registry is unreachable: Claude says which, with the
  command or setting to fix it, and stops.
- The commits are made: Claude shows them and pushes only after the user says yes; without a yes
  nothing is pushed.
