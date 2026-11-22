# Give Claude a Docker Guideline when it works on a Dockerfile or a Compose file

2026-11-22

## Symptom

Claude writing a Dockerfile or a Compose file in a project with louie on gets no rules for it,
and the mistakes it then makes don't fail the build: an image running as root, an Env file
copied into the image (a Leak), Compose's obsolete `version:` key, a Secret passed as an `ARG`.
Build PRD docker: the `docker` Guideline, the Hook and verifier signals for it, the Assessment's
count, and its eval cases.

## Evidence

- This machine's Docker files on 2026-11-22: 6 of 17 Dockerfiles run as root, 6 build from a
  folder with no `.dockerignore`, 5 of 9 Compose files carry `version:`.
- louie 0.73.0 gives no Guideline on a Read of a `Dockerfile` or a `compose.yaml`:
  `plugins/louie/scripts/louie/guidelines.py` `BY_PATH` names none for them.

## Acceptance criteria

- Every acceptance criterion of PRD docker (`.about/prd/docker.md`) passes.
- ADR guidelines names `docker` among the stacks, the Docker files among the Hook's signals, the
  verifier's signal for it, and its Assessment count before the first Edit, not a Write.
- `mise run check` passes.

## Comments

### 2026-11-22 · where it changes

From a fresh read of the PRD against 0.73.0's code:
- louie: `guidelines.py`'s `BY_PATH` (the file-name matcher, from the repo's root, so a basename
  match needs no `sh` filter), the `Guideline(...)` list with its line "Writing a Dockerfile or a
  Compose file", and `fitting()`'s walk for the verifier; `SKIPPED` already holds `node_modules`
  and `dist`. Leaving `docker` off session start's index follows from its being in `BY_PATH`.
- bagheera: `assess.py`'s `_BY_KIND` is its own copy of the matcher (ADR plugin), so the names go
  in both. `condense._EDITS` counts a Write as an edit, so "before the first Edit, a creating
  Write counted neither way" needs the Assessment to tell them apart for `docker`.
- evals: four cases under `evals/docker/`, in the shape of `evals/python/`. The graders there are
  regexes on one fixed path; `dockerignore`'s criterion spans two files (`.dockerignore` or the
  `Dockerfile`), so it needs another grader shape or an `llm` judge.

### 2026-11-22 · order

Write the four eval cases and run each without louie first: a rule whose case scores 1.00
without it on both models is dropped from `docker.md` with its case (PRD docker), so the
Guideline's text waits for those runs.
