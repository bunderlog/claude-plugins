"""Session start, the SessionStart Hook's part (ADR binary): it writes no file in the repo, no
Claude Code setting and no Git hook (PRD no-config, ADR git-hooks). What it prints Claude Code adds
to Claude's context, so it prints only what Claude should know: how many items the Inbox holds (ADR
inbox), the files in .about/ git hasn't committed (ADR about-folder), and the problems, each on one
line; then the Guidelines that fit the repo (ADR guidelines). In a Session review's session, which
bagheera starts, it only names the Guidelines.

Each part returns its own Lines, and session start only gathers them, in the order of PARTS: a new
part is a function and its place there."""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TextIO

from baloo import (
    binlink,
    repo,
    hook,
    inbox,
    names,
)
from baloo.checks.git import Error as GitError, git


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


def _inbox(s: Start) -> Lines:
    return Lines(inbox.lines(s.root) if s.root else [])


def _uncommitted_about(s: Start) -> Lines:
    """The files in .about/ with changes git hasn't committed, new ones too, for the user to
    commit (ADR about-folder): not the Proposals, and nothing in a headless session."""
    if not s.root or hook.headless():
        return Lines()
    try:
        out = git(s.root, "status", "--porcelain", "-z", "--untracked-files=all", "--",
                  ".about")
    except (GitError, OSError) as e:
        return Lines(problems=[f".about/ changes: {e}"])
    files = []
    entries = iter(out.split("\0"))
    for entry in entries:
        path = entry[3:]
        if entry[:1] in ("R", "C"):
            next(entries, "")  # a rename's or a copy's old path
        if path.startswith(".about/") and not path.startswith(names.PROPOSALS):
            files.append(path)
    files.sort()
    if not files:
        return Lines()
    return Lines([
        f".about/ has changes git hasn't committed: {', '.join(files)}: tell the user, and that "
        "committing them is theirs"
    ])


# The parts session start reports on, in the order it prints their lines; the Guidelines' index
# comes after them all.
PARTS: List[Callable[[Start], Lines]] = [
    _inbox,
    _uncommitted_about,
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
            pass  # the Status line and the old Git hooks, which run through it, say so
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
