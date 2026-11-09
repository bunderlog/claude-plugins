"""Session start, the SessionStart Hook's part (ADR binary): it creates the repo's Config when it
has none (ADR config), reads it, picks the Output style it names where Claude Code's settings pick
none (ADR output-styles), and sets the Status line or takes it out (ADR status-line); it writes no
Git hook (ADR git-hooks). What it prints Claude Code adds to Claude's context, so it prints only
what Claude should know: a Config it created, an Output style or a Status line it set, a Hook
Check it turns off (ADR checks), a Session review still running and the Proposals waiting for the user
(ADR session-review), how many items the Inbox holds (ADR inbox), the files in .about/ git hasn't
committed (ADR about-folder), and the problems, each on one line; then the Guidelines the Config turns on (ADR guidelines). In a Session review's session it
only names the Guidelines: that session changes nothing but its Proposals (ADR session-review).

Each part returns its own Lines, and session start only gathers them, in the order of PARTS: a new
part is a function and its place there."""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass, field
from typing import Callable, List, Optional, TextIO

from baloo import (
    binlink,
    checks,
    config,
    guidelines,
    hook,
    inbox,
    names,
    outputstyle,
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

    def setting(
        self, path: str, enabled: str, line: str, err: Optional[BaseException], err_prefix: str
    ) -> None:
        """Adds what a part that wrote a setting returned, as outputstyle.pick and
        settings.set_unset do: `line`, with the team-commit suffix where `enabled` is the project's
        settings, when `path` is set; `err` under `err_prefix` otherwise."""
        if path:
            if enabled == settings.PROJECT:
                line += "; the change to the team's settings is theirs to commit"
            self.lines.append(line)
        self.fail(err_prefix, err)


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
        f"created {s.created} with every check on and the guidelines that fit the repo: tell the "
        "user, and that the file is theirs to commit and to change"
    ])


def _output_style(s: Start) -> Lines:
    c, out = s.config, Lines()
    if not c.output_style:
        return out
    picked, err = outputstyle.pick(s.dir, c.root, c.output_style)
    line = (
        f"picked the {names.PLUGIN}:{c.output_style} output style in {picked.path}: tell the user, "
        "that it applies from their next message or session, and that to drop it they set "
        f"output-style: false in {names.CONFIG} and pick another style, Default too, with "
        "/output-style"
    )
    out.setting(
        picked.path, picked.enabled, line, err,
        f"could not pick the {names.PLUGIN}:{c.output_style} output style",
    )
    return out


def _status_line(s: Start) -> Lines:
    c, out = s.config, Lines()
    if not c.root or c.status_line is None:
        return out
    shown, err = statusline.set_line(s.dir, c.root, s.data, c.status_line)
    if shown:
        out.lines.append(
            f"set the {names.PLUGIN} status line in "
            f"{os.path.join(s.dir, names.LOCAL_SETTINGS)}: tell the user, that it shows from "
            f"their next message, and that status-line: false in {names.CONFIG} takes it out"
        )
    out.fail("could not set the status line", err)
    return out


def _hook_checks_off(s: Start) -> Lines:
    out = Lines()
    for name in checks.HOOK_CHECKS:
        if s.config.checks.get(name) is False:
            out.lines.append(
                f"claude-hooks.{name}: false in {names.CONFIG} turns off a check in Claude Code's "
                "hooks: tell the user"
            )
    return out


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


def _stack_off(s: Start) -> Lines:
    """The Guidelines the repo now has the stack of but the Config turns off, each named once a
    repo, for the user to turn on: not where session start just made the Config, which fits the
    repo already, and nothing in a headless session, which nobody reads."""
    if not s.config.root or s.created or not s.data or review.headless():
        return Lines()
    digest = hashlib.sha256(s.config.root.encode()).hexdigest()[:16]
    folder = os.path.join(s.data, "guidelines", "stack-told", digest)
    try:
        told = set(os.listdir(folder))
    except OSError:
        told = set()
    on = {n: bool(s.config.guidelines.get(n)) or n in told for n in guidelines.names()}
    new = guidelines.fitting_but_off(s.config.root, on)
    if not new:
        return Lines()
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        for name in new:
            with open(os.path.join(folder, name), "w"):
                pass
    except OSError as e:
        return Lines(problems=[f"guidelines of the repo's stack: {e}"])
    one = len(new) == 1
    return Lines([
        f"the repo has what the {', '.join(new)} Guideline{'' if one else 's'} "
        f"cover{'s' if one else ''}, but {names.CONFIG} turns {'it' if one else 'them'} off: tell "
        f"the user, and that turning {'it' if one else 'them'} on there is theirs"
    ])


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
    _stack_off,
    _output_style,
    _status_line,
    _hook_checks_off,
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
        index, _ = hook.guideline_index(config.read(dir).guidelines)
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
    index, why = hook.guideline_index(c.guidelines)
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
