"""The repo's Inbox, `.about/inbox.md`: what is still to consider, one `## ` heading per item (ADR
inbox)."""

from __future__ import annotations

import os
import re
from typing import List, Tuple

from baloo import names

# Ends the date line of an item the user went through once and kept.
_KEPT_MARK = re.compile(r" · kept \d{4}-\d{2}-\d{2}\s*$")


def items(root: str) -> Tuple[int, int]:
    """How many items the Inbox of the repo at `root` holds, one per `## ` heading outside a fenced
    code block, and how many of them are kept; 0 without one."""
    try:
        with open(os.path.join(root, names.INBOX), encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return 0, 0
    n = kept = 0
    fenced, dated = False, True
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced, dated = not fenced, True
        elif fenced:
            pass
        elif line.startswith("## "):
            n += 1
            dated = False
        elif not dated and line.strip():
            # The first line after the heading is the item's date line.
            dated = True
            if _KEPT_MARK.search(line):
                kept += 1
    return n, kept


def lines(root: str) -> List[str]:
    """What session start tells Claude of the Inbox of the repo at `root`: how many items it holds
    and how many aren't gone through yet, for Claude to tell the user; nothing of an empty one."""
    n, kept = items(root)
    if n == 0:
        return []
    left = ""
    if kept == n:
        left = ", each gone through once and kept"
    elif kept > 0:
        left = f", {n - kept} not gone through yet"
    return [
        f"{names.INBOX} holds {n} {'item' if n == 1 else 'items'} to consider{left}: tell the "
        f"user, and that /{names.PLUGIN}:inbox goes through them"
    ]
