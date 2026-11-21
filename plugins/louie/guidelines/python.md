# Python

For writing Python: the choices where more than one would be reasonable, and that show only on
another machine. These are defaults: in an existing codebase, its documented conventions and the
pattern its code already follows win.

## 1. The oldest Python the project supports

- Code runs on the oldest Python the project names: `requires-python` in `pyproject.toml`,
  `python_requires` in `setup.py` or `setup.cfg`, `.python-version`, `mise.toml`, a CI matrix,
  its CLAUDE.md or AGENTS.md. Where none names one, on what the code already uses.
- Below 3.10, no `X | Y` and no `X | None` where Python evaluates it: a parameter's, a return's,
  a module's or a class's variable annotation (a dataclass field) in a module without `from
  __future__ import annotations`, a type alias, a default, `isinstance`, `cast`. Write `Optional[X]` and `Union[X, Y]` from `typing` instead, or add the
  future import where the module's annotations are only annotations. No `match` statement:
  an `if`/`elif` chain instead.

**Test:** every annotation, alias and statement in the change runs on the project's oldest Python.

## 2. An explicit encoding

- `open()` in text mode, `Path.open()`, `Path.read_text` and `write_text` name
  `encoding="utf-8"`, or the encoding the data is in. Without one, Python uses the locale's, which
  is cp1252 on Windows, and a file that isn't ASCII reads wrong there or fails.
- A `subprocess` call that reads its output as text names it too: `text=True,
  encoding="utf-8"`, or bytes decoded with `.decode("utf-8")`. No `os.popen` or
  `subprocess.getoutput`, which take the locale's.

**Test:** every file and every command's output the change reads or writes as text names its
encoding.
