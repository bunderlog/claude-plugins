# louie gives Claude a Python Guideline when it works on a `.py` file

## Problem

Claude writing Python in a project with louie on gets no stack rules, where Go, TypeScript and Vue
code gets its Guideline from a Hook (ADR guidelines). This repo is itself Python (ADR binary), and
two choices a bare model gets wrong show up only on another machine: code that needs a newer
Python than the project supports, and a file or a subprocess's output read without an encoding,
which on Windows decodes as cp1252.

## Users

- Everyone in a project with louie on who has Claude write or change Python, this repo first.
- Not for: a project that wants its own Python rules instead; its documented conventions win over
  the Guideline, as for every stack.

## Success signal

- Each rule in `python.md` has an eval case that fails without louie (ADR evals); a rule no case
  fails without is not in the file.
- In the Assessment after its Release, `python` is in context before the first edit of a `.py`
  file in most sessions with one, as the Guidelines a Hook gives were (15 of 22, ADR guidelines).

## Scope

- `plugins/louie/guidelines/python.md`, in the shape of `go.md` and `typescript.md` (numbered
  sections, each ending in a **Test:** line), the project's documented conventions and its code's
  pattern winning. Its rules, each kept only once its case fails without louie:
  1. **The oldest Python the project supports.** Code runs on the floor the project names
     (`requires-python`, `.python-version`, `mise.toml`, a CI matrix, CLAUDE.md or AGENTS.md); where
     none names one, on what the code already uses. Below 3.10, no `X | Y` and below 3.9 no
     `list[str]` where Python evaluates them (an alias, `isinstance`, `cast`, a default, an
     annotation without `from __future__ import annotations`), and no `match`.
  2. **An explicit encoding.** `open()` in text mode, `Path.read_text`/`write_text` and a
     `subprocess` call with `text=True` name `encoding="utf-8"`, or the encoding the data is in.
- louie's `PostToolUse` Hook gives it whole, once a session, on a Read, Edit, Write or MultiEdit of
  a `.py` or `.pyi` file in the repo, and logs it in `guidelines/guidelines.log`, as `go` on a
  `.go` file.
- Session start's index doesn't name it, as for `go`: the Hook gives it.
- The verifier is given it, as it is the other Guidelines that fit the repo, where the repo holds a
  `.py` file outside the folders session start's walk skips. This repo has no `pyproject.toml`,
  so a manifest can't tell it.
- bagheera's Assessment counts `python` before the first edit of a `.py` or `.pyi` file, as it
  counts `go` before a `.go` file's.
- ADR guidelines names `python` among the stacks, `.py` and `.pyi` among the Hook's signals, and the
  verifier's signal for it.

## Non-goals

- A session start index line for `python`, or a stack told from `pyproject.toml`, `setup.py` or
  `requirements.txt`.
- Formatting or lint rules a tool already checks (ruff, black, isort).
- Other rules (subprocess without a shell, narrow `except`, type hints, dataclasses): each comes
  only with a case that fails without louie.
- Notebooks (`.ipynb`), Cython (`.pyx`), or a framework's rules (Django, FastAPI).
- A new module written before Claude touches any `.py` file: the Hook gives a Guideline after the
  Write that creates the file, as for `go` (ADR guidelines).
- Guidelines for the other stacks still in the Inbox.

## Anti-goals

- A rule that contradicts this repo's own (standard library only, Python 3.9, `unittest`): the
  repo's CLAUDE.md wins, and a Guideline that makes Claude argue with it is a failure.
- `python` given where no Python is touched, or more than once in a session.

## Acceptance criteria

- A Read of a `.py` file in the repo gives `python.md` whole as added context, and the log has one
  line naming the session, `python` and the file; a second Read or an Edit of a `.py` file in the
  same session gives no `python` again.
- A Read of a `.pyi` file gives it as a `.py` file does; a Read of a `.pyx`, `.ipynb` or
  `pyproject.toml` file gives no `python`.
- A Read of a `.py` file outside the repo gives no `python`.
- Session start's index names no `python` line, in a repo with `.py` files or without.
- The verifier's start gives a `python` line in a repo with a `.py` file, here among them, and none
  in a repo whose only `.py` files are under `node_modules/` or `dist/`.
- The Assessment counts a session that read a `.py` file, was given `python`, then edited it, as
  `python` in context before the first edit; one that edited a `.py` file with no `python` given
  first, as not.
- `evals/python/version`: in a repo whose `pyproject.toml` says `requires-python = ">=3.9"`,
  Claude, asked to add an optional parameter to a function in an existing `.py` file, writes no
  `X | None` or `match` that Python 3.9 would evaluate; it scores below 1.00 without louie on at
  least one of the default model and Claude Sonnet, and 1.00 with it on both, 3 runs an arm.
- `evals/python/encoding`: Claude, asked to make an existing `.py` file read a text file and a
  `git` command's output, names an encoding on each; scored as above.
