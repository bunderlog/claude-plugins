"""The project's ADRs and PRDs that the PostToolUse Hook names at a file Claude reads, edits or
writes, once a session each (PRD index): those whose text names the file, and that Claude hasn't
read with the Read tool in the session."""

from __future__ import annotations

import os
import re
import time
from typing import List, NamedTuple

from louie import hook
from louie.names import ADRS, PRDS

# A path of two or more segments in an ADR's or a PRD's text; copied from bagheera's Assessment,
# which counts the reads before an edit by the same rule, since the plugins share no code (ADR
# plugin).
PATH = re.compile(r"[\w.@-]+(?:/[\w.@-]+)+")

# The most ADRs and PRDs named at a file at once; the rest are named at the next call.
MOST = 5

# How long what a session was told of them is kept: a week, as the Guidelines' marks.
KEPT = 7 * 24 * 3600


def names(path: str, rel: str) -> bool:
    """Whether `path`, found in an ADR's or a PRD's text, names the repo's file `rel`."""
    folder = os.path.dirname(rel)
    for whole in (rel, folder):
        if whole and (whole == path or whole.endswith("/" + path)):
            return True
    return False


class _Doc(NamedTuple):
    """An ADR or a PRD: its path from the repo's root, its title, "" where it has none, and the
    paths its text holds."""

    path: str
    title: str
    paths: List[str]


def _docs(root: str) -> List[_Doc]:
    """The ADRs of the repo at `root`, the `*.md` files directly in `.about/adr/`, then its PRDs in
    `.about/prd/`, each kind by file name. A title is the first line outside a fenced code block
    that starts with `# `, as baloo's session start takes it; a file that can't be read is left
    out."""
    got: List[_Doc] = []
    for kind in (ADRS, PRDS):
        folder = os.path.join(root, kind)
        try:
            entries = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in entries:
            file = os.path.join(folder, name)
            if name.startswith(".") or not name.endswith(".md") or not os.path.isfile(file):
                continue
            try:
                with open(file, encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            got.append(_Doc(kind + name, _title(text), PATH.findall(text)))
    return got


def _title(text: str) -> str:
    fenced = False
    for line in text.split("\n"):
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("# "):
            return hook.one_line(line[2:].rstrip("\r"))
    return ""


def mark_read(data: str, session: str, rel: str) -> None:
    """Notes a Read of the file at `rel`, from the repo's root: an ADR or a PRD read isn't named
    again in the session."""
    rel = rel.replace(os.sep, "/")
    if os.path.dirname(rel) + "/" in (ADRS, PRDS):
        _mark(data, session, [rel])


def for_file(data: str, session: str, root: str, rel: str) -> str:
    """What Claude is to be told of the ADRs and PRDs of the repo at `root` that name the file at
    `rel`, from its root, and that the session `session` was neither told of nor read: a line each,
    the first MOST of them, which are marked in the plugin's data folder `data`, and a line for
    how many more name it. It is "" where none is due, without a data folder or a session, and for
    a file in any `.about/` folder, which is the project's knowledge, not its code. A mark it
    can't write raises OSError."""
    rel = rel.replace(os.sep, "/")
    if not data or not session or rel.startswith(".about/") or "/.about/" in rel:
        return ""
    if not os.path.isdir(os.path.join(root, ".about")):
        return ""
    seen = set(_lines(_marks(data, session)))
    due = [
        d for d in _docs(root) if d.path not in seen and any(names(p, rel) for p in d.paths)
    ]
    if not due:
        return ""
    now, later = due[:MOST], due[MOST:]
    lines = [
        f"The project's ADRs and PRDs that name {hook.one_line(rel)}: read them before you edit "
        "it, and say where the code already breaks one."
    ]
    lines += [f"{d.path}: {d.title}" if d.title else d.path for d in now]
    if later:
        folders = [k for k in (ADRS, PRDS) if any(d.path.startswith(k) for d in later)]
        lines.append(
            f"{len(later)} more name it, in {' and '.join(folders)}: they are named at the next "
            "file one of them names."
        )
    _mark(data, session, [d.path for d in now])
    return "\n".join(lines)


def _marks(data: str, session: str) -> str:
    return os.path.join(data, "about", "shown", session)


def _mark(data: str, session: str, paths: List[str]) -> None:
    """Adds `paths` to what the session `session` was told of or read, and forgets what sessions
    were a week ago."""
    if not data or not session:
        return
    file = _marks(data, session)
    folder = os.path.dirname(file)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    _forget(folder)
    had = _lines(file)
    new = [p for p in paths if p not in had]
    if not new:
        return
    fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(had + new) + "\n")


def _lines(file: str) -> List[str]:
    """The lines of the file at `file`, none where it can't be read."""
    try:
        with open(file, encoding="utf-8") as f:
            return [line for line in f.read().splitlines() if line]
    except OSError:
        return []


def _forget(folder: str) -> None:
    """Deletes what sessions were told more than a week ago."""
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return
    now = time.time()
    for e in entries:
        try:
            if now - e.stat().st_mtime > KEPT:
                os.remove(e.path)
        except OSError:
            pass
