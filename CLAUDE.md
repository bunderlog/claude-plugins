# CLAUDE.md

This repo is baloo's own source: `plugins/baloo/` is what ships (skills, the agent, Guidelines,
Hooks, the Output style, the schema, and in `scripts/` the Python code the Hooks run, standard
library only, Python 3.9 and later), `tests/` tests that code, and `src/release/release.py` makes
and tags Releases. A session here runs the plugin from the last Release, not this checkout — see
README.md's Development section for trying an edit to a skill, the agent, a Guideline or a Hook
first.

`.about/` holds this project's own decisions (ADRs, glossary, Inbox) — read it before proposing
an architecture change or a new domain term; don't reopen what it already settled.

`mise run check` runs what CI runs: the tests in `tests/` on Python 3.9, `ruff check` on the Python,
and `shellcheck` on `plugins/baloo/scripts/hook`. `mise run release` cuts and pushes a Release, but
only counts commits under `plugins/baloo/`, the schema aside (ADR releases); a commit outside it —
the tests, this file, the README — just needs a plain push. Commit subjects become the CHANGELOG:
split unrelated changes into a commit per type, and write each subject for users; the format is
`.hathi.yml`'s, which the Git hooks check: @.hathi.yml. A `feat` commit under `plugins/baloo/` names
the feature's PRD in `.about/prd/` in its body, `PRD <feature>`, and a `fix` the PRD, ADR or Issue
it brings the code back to, so a Verification finds it; a feature without a PRD gets one first (PRD
harness).

See README.md for Format on edit, the doctor and development in full.
