"""Session start, the SessionStart Hook's part (ADR binary): it creates the repo's Config when it
has none (ADR config) and reads it; it writes no Claude Code setting and no Git hook (PRD
no-config, ADR git-hooks). What it prints Claude Code adds to Claude's context, so it prints only
what Claude should know: a Config it created, once per clone how the person sets their own Output
style and Status line, a Session review still running and the Proposals waiting for the user (ADR
session-review), how many items the Inbox holds (ADR inbox), the files in .about/ git hasn't
committed (ADR about-folder), and the problems, each on one line; then the Guidelines that fit the
repo (ADR guidelines). In a Session review's session it only names the Guidelines: that session
changes nothing but its Proposals (ADR session-review).

Each part returns its own Lines, and session start only gathers them, in the order of PARTS: a new
part is a function and its place there."""

from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TextIO

from baloo import (
    binlink,
    config,
    hook,
    inbox,
    names,
    review,
    settings,
    statusline,
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
    """What each part works from: the folder Claude Code runs in, its repo's Config, the path of a
    Config session start created, or "", the plugin's data folder, and the session's id."""

    dir: str
    config: config.Config
    created: str
    data: str
    session: str


def _config(s: Start) -> Lines:
    if not s.created:
        return Lines()
    return Lines([
        f"created {s.created}: tell the user, and that the file is theirs to commit and to change"
    ])


def _personal(s: Start) -> Lines:
    """Once per clone, how to set an Output style and a Status line in the person's own settings,
    for each no settings file sets: the plugin sets neither (PRD no-config). A headless session is
    told nothing, so it doesn't use up the telling."""
    if not s.config.root or not s.data or review.headless():
        return Lines()
    try:
        fields = settings.read_all(settings.files(s.dir))
    except (OSError, ValueError):
        return Lines()
    unset = [k for k in ("outputStyle", "statusLine") if not any(k in f for f in fields.values())]
    digest = hashlib.sha256(s.config.root.encode()).hexdigest()[:16]
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
    fields_text = ", ".join(f'"{k}": {values[k]}' for k in new)
    return Lines([
        f"{names.PLUGIN} no longer picks an Output style or sets a Status line; to keep its own, "
        f"the user adds to ~/.claude/settings.json: {fields_text}: tell the user, once"
    ])


def _session_review(s: Start) -> Lines:
    out = Lines()
    if not s.config.root:
        return out
    if review.running(s.config.root, s.data) and not review.headless():
        out.lines.append(
            "a Session review of an earlier session is still running: its proposals come with a "
            "later prompt"
        )
    out.lines.extend(review.show(s.config.root, s.data, s.session, hook.decide_command()))
    return out


def _inbox(s: Start) -> Lines:
    return Lines(inbox.lines(s.config.root) if s.config.root else [])


def _uncommitted_about(s: Start) -> Lines:
    """The files in .about/ with changes git hasn't committed, new ones too, for the user to
    commit (ADR about-folder): not the Proposals, and nothing in a headless session."""
    if not s.config.root or review.headless():
        return Lines()
    try:
        out = git(s.config.root, "status", "--porcelain", "-z", "--untracked-files=all", "--",
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
    _config,
    _personal,
    _session_review,
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
    if os.environ.get(review.ENV, ""):
        index, _ = hook.guideline_index(config.read(dir).root)
        if index:
            stdout.write(index + "\n")
        return 0
    c, created, problems = config.load(dir)
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if data:
        # The link tells a later prompt that this version's session start ran (see cli).
        try:
            binlink.point(data)
        except OSError:
            pass  # the Status line and the Git hooks, which run through it, say so
    s = Start(dir, c, created, data, session)
    out = Lines(problems=list(problems))
    for part in PARTS:
        got = part(s)
        out.lines.extend(got.lines)
        out.problems.extend(got.problems)
    index, why = hook.guideline_index(c.root)
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
