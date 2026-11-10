"""Session start, the SessionStart Hook's part (PRD bagheera): it writes no file in the repo and
no Claude Code setting. What it prints Claude Code adds to Claude's context, so it prints only what
Claude should know: once per clone how the person sets their own Output style and Status line, a
Session review still running and the Proposals waiting for the user (ADR session-review), and the
problems, each on one line. In a Session review's session it prints nothing.

Each part returns its own Lines, and session start only gathers them, in the order of PARTS: a new
part is a function and its place there."""

from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TextIO

from bagheera import (
    binlink,
    repo,
    hook,
    names,
    review,
    settings,
    statusline,
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


# The mark in the clone's told folder that the old Output style was told of.
OLD_STYLE_TOLD = "old-outputStyle"


def _personal(s: Start) -> Lines:
    """Once per clone, how to set an Output style and a Status line in the person's own settings,
    for each no settings file sets: the plugin sets neither (PRD no-config); and where a settings
    file still picks baloo's `short-replies`, which Claude Code no longer finds, to pick bagheera's
    (PRD bagheera). A headless session is told nothing, so it doesn't use up the telling."""
    if not s.root or not s.data or review.headless():
        return Lines()
    paths = settings.files(s.dir)
    try:
        fields = settings.read_all(paths)
    except (OSError, ValueError):
        return Lines()
    unset = [k for k in ("outputStyle", "statusLine") if not any(k in f for f in fields.values())]
    old = [paths[k] for k, f in fields.items() if f.get("outputStyle") == names.OLD_STYLE]
    if old:
        unset.append(OLD_STYLE_TOLD)
    digest = hashlib.sha256(s.root.encode()).hexdigest()[:16]
    folder = os.path.join(s.data, "personal-told", digest)
    try:
        told = set(os.listdir(folder))
    except OSError:
        told = set()
    new = [k for k in unset if k not in told]
    if not new:
        return Lines()
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        for key in new:
            with open(os.path.join(folder, key), "w"):
                pass
    except OSError as e:
        return Lines(problems=[f"personal settings: {e}"])
    values = {
        "outputStyle": json.dumps(f"{names.PLUGIN}:short-replies"),
        "statusLine": json.dumps({
            "type": "command",
            "command": statusline.command(os.path.join(s.data, names.PLUGIN)),
            "padding": 0,
            "refreshInterval": 60,
        }),
    }
    out = Lines()
    keys = [k for k in new if k != OLD_STYLE_TOLD]
    if keys:
        fields_text = ", ".join(f'"{k}": {values[k]}' for k in keys)
        out.lines.append(
            f"{names.PLUGIN} no longer picks an Output style or sets a Status line; to keep its "
            f"own, the user adds to ~/.claude/settings.json: {fields_text}: tell the user, once"
        )
    if OLD_STYLE_TOLD in new:
        out.lines.append(
            f"{', '.join(old)} picks the Output style {names.OLD_STYLE}, which is "
            f"{names.PLUGIN}'s now and no longer found under that name: to keep it, the user sets "
            f'"outputStyle": {values["outputStyle"]} there: tell the user, once'
        )
    return out


def _session_review(s: Start) -> Lines:
    out = Lines()
    if not s.root:
        return out
    if review.running(s.root, s.data) and not review.headless():
        out.lines.append(
            "a Session review of an earlier session is still running: its proposals come with a "
            "later prompt"
        )
    out.lines.extend(review.show(s.root, s.data, s.session, hook.decide_command()))
    return out


# The parts session start reports on, in the order it prints their lines.
PARTS: List[Callable[[Start], Lines]] = [
    _personal,
    _session_review,
]


def run(session: str, stdout: TextIO, stderr: TextIO) -> int:
    """Runs session start for the session `session`, printing what it tells Claude to `stdout`,
    and returns its exit code."""
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{names.PLUGIN}: {e}\n")
        return 1
    if os.environ.get(review.ENV, ""):
        return 0
    root = repo.root(dir)
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if data:
        # The link tells a later prompt that this version's session start ran (see cli).
        try:
            binlink.point(data)
        except OSError:
            pass  # the Status line, which runs through it, says so
    s = Start(dir, root, data, session)
    out = Lines()
    for part in PARTS:
        got = part(s)
        out.lines.extend(got.lines)
        out.problems.extend(got.problems)
    lines = [hook.one_line(line) for line in out.lines + out.problems]
    if lines:
        stdout.write(f"{names.PLUGIN}:\n" + "\n".join(lines) + "\n")
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
