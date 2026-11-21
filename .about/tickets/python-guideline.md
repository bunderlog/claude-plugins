# Give Claude the python Guideline when it works on a `.py` file

2026-11-21

## Symptom

Claude writing Python with louie on gets no stack Guideline, where `.go`, `.ts` and `.vue` files
bring theirs (ADR guidelines). Build PRD python: `plugins/louie/guidelines/python.md` with its two
rules, given by the Hook on a `.py` or `.pyi` file, named to the verifier in a repo with Python,
counted by the Assessment, and its eval cases in `evals/python/`.

## Evidence

- `plugins/louie/scripts/louie/guidelines.py`: `BY_PATH` has `go`, `typescript`, `vue` and
  `writing-for-agents`, no `python`; `GUIDELINES` has no `python` entry for the verifier's index.
- `plugins/bagheera/scripts/bagheera/assess.py:54`: `_BY_KIND` counts only `go`, `typescript`,
  `vue` and `writing-for-agents`.
- `.about/adr/guidelines.md` names no `python` among the stacks or the Hook's signals.
- This repo has `.py` files and no `pyproject.toml`; its floor is Python 3.9 (`mise.toml`, ADR
  binary).

## Acceptance criteria

- Every criterion of PRD python (`.about/prd/python.md`, Acceptance criteria).
- `python.md` holds only the rules whose case in `evals/python/` fails without louie; a rule whose
  case passes without it on both models is left out, and the run's scores go in the pull request.

## Comments

### 2026-11-21 · fix option

The Hook's signal is one line in `BY_PATH`, `"python": _has_ext(".py", ".pyi")`. The verifier's
needs a fact from session start's walk: whether the repo holds a `.py` file outside the skipped
folders, beside `go_mod`. The Assessment's is one line in `_BY_KIND`, mirroring `go`.

### 2026-11-21 · fix option

The eval cases need a scaffold with an existing `.py` file the prompt asks Claude to change: a
Write that creates a file gives the Guideline only after it (ADR guidelines). Grade by regex over
the changed file, as ADR evals asks: `| None` outside an annotation under `from __future__ import
annotations`, or `match `, for `version`; an `open(` in text mode, `read_text`, `write_text` or
`text=True` with no `encoding=` for `encoding`.

### 2026-11-21 · decision

If neither case in `evals/python/` fails without louie on either model, no rule is left for
`python.md`: stop before the pull request merges, report the scores, revise PRD python, and ship
no python Guideline, Hook, verifier or Assessment wiring. A Guideline with no rules is context paid
for nothing, and ADR evals keeps a rule only on a failing case.
