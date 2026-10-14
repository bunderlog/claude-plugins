"""The Check no-large-files."""

# cspell:ignore objectsize

from __future__ import annotations

import re
from typing import List

from baloo.checks.git import Error, git

# The largest file no-large-files lets a commit add without a setting, in KB.
DEFAULT_MAX_FILE_KB = 1024


def no_large_files(dir: str, max_kb: int) -> List[str]:
    """The Check baloo:no-large-files (pre-commit): `<path>: <size> KB, over <max> KB` for each
    file the staged changes of the repo `dir` add over `max_kb` KB, of 1024 bytes;
    DEFAULT_MAX_FILE_KB for 0. A file already committed passes, changed or renamed too, and so does
    a submodule. It raises an Error where git fails, such as outside a repo."""
    max_kb = max_kb or DEFAULT_MAX_FILE_KB
    # Each file added is `:<old mode> <new mode> <old id> <new id> A`, then its path.
    raw = git(dir, "diff", "--cached", "-M", "--diff-filter=A", "--raw", "-z", "--no-abbrev")
    paths, ids = [], []
    fields = raw.removesuffix("\0").split("\0")
    for i in range(0, len(fields) - 1, 2):
        f = fields[i].split()
        if len(f) != 5 or f[1] == "160000":
            continue
        paths.append(fields[i + 1])
        ids.append(f[3] + "\n")
    if not paths:
        return []
    sizes = git(dir, "cat-file", "--batch-check=%(objectsize)", stdin="".join(ids))
    found = []
    for i, line in enumerate(sizes.removesuffix("\n").split("\n")):
        if not re.fullmatch(r"[+-]?[0-9]+", line) or i >= len(paths):
            raise Error(f'git cat-file: "{line}" is not a size')
        size = int(line)
        if size > max_kb * 1024:
            found.append(f"{paths[i]}: {(size + 1023) // 1024} KB, over {max_kb} KB")
    return found
