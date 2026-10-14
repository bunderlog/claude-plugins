"""The Check no-conflict-markers."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Dict, List

from baloo.checks.git import Error, git

# Ends a line of `git diff --check` for a conflict marker.
_LEFTOVER = ": leftover conflict marker"


def no_conflict_markers(dir: str) -> List[str]:
    """The Check baloo:no-conflict-markers (pre-commit): `<path>:<line>` for each conflict marker
    the staged changes of the repo `dir` add, as git's own `diff --check` finds them, in a file
    where one of them opens or closes a conflict: a Markdown heading underlined with `=======`
    alone passes, and so does a file whose conflict-marker-size in .gitattributes is longer. It
    raises an Error where git fails, such as outside a repo."""
    p = subprocess.run(
        ["git", "-C", dir, "-c", "core.quotePath=false", "diff", "--cached", "--check", "--no-color"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "LC_ALL": "C"},  # git's own words, which the lines are told by
    )
    # It exits 2 where it finds a marker or a whitespace error.
    if p.returncode not in (0, 2):
        raise Error(f"git diff: exit status {p.returncode}: {p.stderr.strip()}")
    lines: Dict[str, List[int]] = {}
    for text in p.stdout.split("\n"):
        if not text.endswith(_LEFTOVER):
            continue
        path, colon, n = text[: -len(_LEFTOVER)].rpartition(":")
        if not colon or not re.fullmatch(r"[+-]?[0-9]+", n):
            continue
        lines.setdefault(path, []).append(int(n))
    found = []
    for path, numbers in lines.items():
        if _opens_conflict(dir, path, numbers):
            found += [f"{path}:{n}" for n in numbers]
    return found


def _opens_conflict(dir: str, path: str, lines: List[int]) -> bool:
    """Whether one of the lines `lines` of the staged file `path` opens or closes a conflict,
    `<<<<<<<` or `>>>>>>>`; it says so too where the file can't be read, such as a path git
    quoted."""
    try:
        text = git(dir, "cat-file", "blob", ":" + path)
    except Error:
        return True
    all_lines = text.split("\n")
    return any(
        1 <= n <= len(all_lines) and all_lines[n - 1][:1] in ("<", ">") for n in lines
    )
