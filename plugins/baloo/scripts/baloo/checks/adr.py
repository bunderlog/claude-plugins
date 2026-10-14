"""The Check no-stale-adr-date."""

from __future__ import annotations

import re
from typing import List

from baloo import names
from baloo.checks.git import git

# An ADR's Date line, ending in LF or CRLF.
_ADR_DATE = re.compile(r"^Date: *(.*?) *\r?$", re.M)


def no_stale_adr_date(dir: str, today: str) -> List[str]:
    """The Check baloo:no-stale-adr-date (pre-commit): `<path>: <why>` for each ADR the staged
    changes of the repo `dir` change without setting its Date to `today`, YYYY-MM-DD. A new ADR and
    a deleted or renamed one pass. It raises an Error where git fails, such as outside a repo."""
    listed = git(
        dir, "diff", "--cached", "--no-renames", "--diff-filter=M", "--name-only", "-z", "--",
        names.ADRS + "*.md",
    )
    found = []
    for path in listed.removesuffix("\0").split("\0"):
        if not path:
            continue
        m = _ADR_DATE.search(git(dir, "cat-file", "blob", ":" + path))
        if m is None:
            found.append(f"{path}: has no Date line; add Date: {today} under its title")
        elif m[1] != today:
            found.append(f"{path}: changed, but its Date is {m[1]}; set it to {today}")
    return found
