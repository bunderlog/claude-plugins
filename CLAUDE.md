# CLAUDE.md

This repo is baloo's own source: `plugins/baloo/` is what ships (skills, the agent, Guidelines,
Hooks, the Output style, the schema), `src/baloo/` is its Go binary, `src/release/` builds and
tags Releases. A session here runs the plugin from the last Release, not this checkout — see
README.md's Development section for trying an edit to a skill, the agent, a Guideline or a Hook
first.

`.about/` holds this project's own decisions (ADRs, glossary, Inbox) — read it before proposing
an architecture change or a new domain term; don't reopen what it already settled.

`mise run check` runs what CI runs: `gofmt`, `go vet`, `go test` for both Go modules
(`src/baloo`, `src/release`), `shellcheck` on the Loader, and `cspell` on the repo.
`mise run release` cuts and pushes a Release, but only counts commits under `plugins/baloo/` and
`src/baloo/`, tests and the schema aside (ADR releases); a commit outside those — this file, the
README — just needs a plain push. Commit subjects become the CHANGELOG: split unrelated changes
into a commit per type, and write each subject for users. A commit that changes a feature with a
PRD in `.about/prd/` names it in its body, `PRD <feature>`, so a Verification finds it.

See README.md for the Git hooks, Format on edit, CI and development in full.
