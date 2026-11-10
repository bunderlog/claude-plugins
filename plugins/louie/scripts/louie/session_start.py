"""Session start, the SessionStart Hook's part (PRD louie): it writes no file in the repo. What it
prints Claude Code adds to Claude's context: the Guidelines that fit the repo, after the rules for
every task (ADR guidelines), and its problems, each on one line.

Each part returns its own Lines, and session start only gathers them, in the order of PARTS: a new
part is a function and its place there."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TextIO

from louie import (
    binlink,
    repo,
    hook,
    names,
)


@dataclass
class Lines:
    """What a part tells Claude: the lines of what it did, and of what went wrong."""

    lines: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)

    def fail(self, prefix: str, err: Optional[BaseException]) -> None:
        """Adds what went wrong, under `prefix`, when `err` is set."""
        if err is not None:
            self.problems.append(f"{prefix}: {err}")


@dataclass
class Start:
    """What each part works from: the folder Claude Code runs in, its repo's root, or "" outside a
    repo (see repo.root), the plugin's data folder, and the session's id."""

    dir: str
    root: str
    data: str
    session: str


# The parts session start reports on, in the order it prints their lines; the Guidelines' index
# comes after them all.
PARTS: List[Callable[[Start], Lines]] = [
]


def run(session: str, stdout: TextIO, stderr: TextIO) -> int:
    """Runs session start for the session `session`, printing what it tells Claude to `stdout`,
    and returns its exit code."""
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{names.PLUGIN}: {e}\n")
        return 1
    if os.environ.get(hook.REVIEW_ENV, ""):
        index, _ = hook.guideline_index(repo.root(dir))
        if index:
            stdout.write(index + "\n")
        return 0
    root = repo.root(dir)
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if data:
        # The link tells a later prompt that this version's session start ran (see cli).
        try:
            binlink.point(data)
        except OSError:
            pass  # a later prompt runs session start again
    s = Start(dir, root, data, session)
    out = Lines()
    for part in PARTS:
        got = part(s)
        out.lines.extend(got.lines)
        out.problems.extend(got.problems)
    index, why = hook.guideline_index(root)
    if why is not None:
        out.problems.append(f"could not name the guidelines: {why}")
    lines = [hook.one_line(line) for line in out.lines + out.problems]
    if lines:
        stdout.write(f"{names.PLUGIN}:\n" + "\n".join(lines) + "\n")
    if index:
        stdout.write(index + "\n")
    return 0


def run_hook(event: str, stdin: str, stdout: TextIO, stderr: TextIO) -> int:
    """Runs session start for the Hook of `event` and writes that Hook's JSON: what session start
    tells Claude, which Claude Code adds to Claude's context; nothing where it has nothing to
    tell. The user sees which Release runs with doctor (ADR doctor). It reads the session's id from
    the Hook's input, where there is one."""
    session = ""
    call = hook.decode(stdin)
    if call is not None:
        try:
            session = hook.text(call, "session_id")
        except hook.Mismatch:
            pass
    context = io.StringIO()
    code = run(session, context, stderr)
    if code == 0 and context.getvalue():
        hook.context(stdout, event, context.getvalue())
    return code
