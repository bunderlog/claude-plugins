# CLAUDE.md

This repo is the `bunderlog` marketplace's source: `plugins/baloo/` (the knowledge skills and one
`sh` session-start Hook), `plugins/louie/` (the Guidelines and the Hooks that give them, the agents
and the Workflows) and `plugins/bagheera/` (the Checks in Hooks, the Status line, doctor, the
Session review, Retro and the Output style) are what ships, louie's and bagheera's Python in their
`scripts/`, standard library only, Python 3.9 and later, sharing no code (ADR plugin);
`tests/<plugin>/` tests each, and `src/release/release.py` makes and tags Releases of all three
under one version. A session here runs the plugins from the last Release, not this checkout — see
README.md's Development section for trying an edit first.

`.about/` holds this project's own decisions (ADRs, glossary, Inbox) — read it before proposing
an architecture change or a new domain term; don't reopen what it already settled.

`mise run check` runs what CI runs: the tests in `tests/` on Python 3.9, louie's Workflows' in
`tests/workflows/` on `node`, `ruff check` on the Python, and `shellcheck` on the Hooks' `sh`. `mise
run release` cuts and pushes a Release, but only counts commits under a plugin's folder in
`plugins/` (ADR releases); a commit outside it — the tests, this file, the README — just needs a
plain push. Commit subjects become the CHANGELOG: split unrelated changes into a commit per type,
and write each subject for users; the format is `.hathi.yml`'s, which the Git hooks check:
@.hathi.yml. A `feat` commit under `plugins/` names the feature's PRD in `.about/prd/` in its body,
`PRD <feature>`, and a `fix` the PRD, ADR or Issue it brings the code back to, so a Verification
finds it; a feature without a PRD gets one first (PRD harness).

See README.md for the settings, the doctor and development in full.
