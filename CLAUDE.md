# CLAUDE.md

This repo is baloo's own source: `plugins/baloo/` is what ships (skills, guidelines, hooks,
output style, schema), `src/baloo/` is its Go CLI, `src/release/` builds and tags Releases.

`.claude/settings.json` installs baloo from GitHub, so a session here runs the **last Release**,
not this checkout. To try an edit to a skill, guideline or hook before a Release, start the
session with `claude --plugin-dir plugins/baloo` — the `baloo` binary itself is still the last
Release's, so changes to `src/baloo/` need a Release (or a local build) to take effect.

`.about/` holds this project's own decisions (ADRs, glossary, inbox) — read it before proposing
an architecture change or a new domain term; don't reopen what it already settled.

`mise run check` runs what CI and the Stop check run: `gofmt`, `go vet`, `go test` for both Go
modules (`src/baloo`, `src/release`), `shellcheck` on the Loader, and `cspell` on the repo.
`mise run release` cuts and pushes a Release.

See README.md for the Git hooks, Stop check, format-on-edit and CI mechanics in full.
