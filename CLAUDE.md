# CLAUDE.md

This repo is baloo's own source: `plugins/baloo/` is what ships (skills, guidelines, hooks,
output style, schema), `src/baloo/` is its Go CLI, `src/release/` builds and tags Releases. A
session here runs the plugin from the last Release, not this checkout — see README.md's
Development section for trying an edit to a skill, guideline or hook first.

`.about/` holds this project's own decisions (ADRs, glossary, inbox) — read it before proposing
an architecture change or a new domain term; don't reopen what it already settled.

`mise run check` runs what CI and the Stop check run: `gofmt`, `go vet`, `go test` for both Go
modules (`src/baloo`, `src/release`), `shellcheck` on the Loader, and `cspell` on the repo.
`mise run release` cuts and pushes a Release, but only counts commits under `plugins/baloo/` and
`src/baloo/` (ADR releases); a commit outside those paths — this file, the README — just needs a
plain push.

See README.md for the Git hooks, Stop check, format-on-edit, CI and development mechanics in full.
