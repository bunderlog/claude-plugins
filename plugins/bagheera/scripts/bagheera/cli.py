"""The plugin's commands, one for each part of the plugin, as its Hooks, Git hooks, Status line
and skills run them through scripts/run.py (ADR binary)."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, TextIO

from bagheera import (
    binlink,
    checks,
    condense,
    doctor,
    hook,
    names,
    once,
    repo,
    review,
    session_start,
    setup,
    statusline,
    version,
)

USAGE = (
    "usage: bagheera version | doctor | setup [--hathi | --no-hathi] |\n"
    "  session-start [UserPromptSubmit] | status-line |\n"
    "  pre-tool-use | session-end | user-prompt-submit |\n"
    "  review-decision <review> <proposal> accepted|accepted-edited|rejected|deferred |\n"
    "  proposals |\n"
    "  condense [--last <n> | <session>...] | condense <session> --around <line>"
)


def main(
    args: Optional[List[str]] = None,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    """Runs the command `args`, by default the process's own, and returns its exit code."""
    if args is None:
        args = sys.argv[1:]
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    return run(
        args,
        sys.stdin if stdin is None else stdin,
        sys.stdout if stdout is None else stdout,
        sys.stderr if stderr is None else stderr,
    )


def run(args: List[str], stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    if len(args) == 1:
        command = args[0]
        if command == "version":
            stdout.write(version.read() + "\n")
            return 0
        if command == "doctor":
            return doctor.run(stdout, stderr)
        if command == "session-start":
            return session_start.run_hook("SessionStart", _read(stdin), stdout, stderr)
        hooks = {
            "status-line": status_line,
            "pre-tool-use": pre_tool_use,
            "session-end": session_end,
            "user-prompt-submit": user_prompt_submit,
        }
        if command in hooks:
            return hooks[command](_read(stdin), stdout)
    # The UserPromptSubmit Hook, in a session the plugin was updated in, runs the session start no
    # SessionStart Hook ran for this version (see user_prompt_submit).
    if args == ["session-start", "UserPromptSubmit"]:
        return session_start.run_hook(args[1], _read(stdin), stdout, stderr)
    if len(args) == 4 and args[0] == "review-decision":
        return review_decision(args[1:], stdout, stderr)
    if args == ["proposals"]:
        return proposals(stdout, stderr)
    if args and args[0] == "setup" and args[1:] in ([], ["--hathi"], ["--no-hathi"]):
        add = {"--hathi": True, "--no-hathi": False}.get(args[1]) if args[1:] else None
        return setup_repo(add, stdout, stderr)
    if args and args[0] == "condense":
        code = condense_sessions(args[1:], stdout, stderr)
        if code is not None:
            return code
    stderr.write(USAGE + "\n")
    return 2


def _read(stdin: Optional[TextIO]) -> str:
    """What Claude Code gives a Hook on stdin; nothing where it gives none."""
    if stdin is None:
        return ""
    try:
        return stdin.read()
    except (OSError, ValueError):
        return ""


def _tool_call(text: str) -> Optional[Dict[str, Any]]:
    """The tool call Claude Code gives a PreToolUse Hook, `text`, where its fields the Checks read
    have their types; None otherwise, as Go's decoder failed the whole call."""
    call = hook.decode(text)
    if call is None:
        return None
    try:
        hook.text(call, "tool_name")
        hook.text(call, "cwd")
        tool_input = hook.object_(call, "tool_input")
        for key in ("command", "file_path", "path", "glob", "content", "new_string"):
            hook.text(tool_input, key)
        edits = tool_input.get("edits")
        if edits is not None:
            if not isinstance(edits, list):
                return None
            for edit in edits:
                if edit is not None:
                    if not isinstance(edit, dict):
                        return None
                    hook.text(edit, "new_string")
    except hook.Mismatch:
        return None
    return call


def status_line(text: str, stdout: TextIO) -> int:
    """Claude Code's status line command (ADR status-line): it prints the Status line for what
    Claude Code gives it on stdin, in a terminal as wide as COLUMNS says, with its default bars
    (PRD no-config). A field of another type than the plugin's is left out, and the rest shows;
    whatever else goes wrong, it prints nothing, since Claude Code shows under the prompt whatever
    it prints."""
    try:
        value, _ = json.JSONDecoder().raw_decode(text.lstrip(" \t\r\n"))
    except ValueError:
        return 0
    in_ = statusline.Input.parse(value)
    columns = os.environ.get("COLUMNS", "")
    width = int(columns) if re.fullmatch(r"[+-]?[0-9]+", columns) else 0
    if width <= 0:
        width = 120
    layout = statusline.default()
    stdout.write(layout.render(in_, statusline.branch(in_.current_dir), width) + "\n")
    return 0


# Ends the reason of a command denied, for Claude to leave it to the user.
_RUN_IT_YOURSELF = (
    ". If it's really needed, ask the user to run it themselves with `! <command>`."
)


def pre_tool_use(text: str, stdout: TextIO) -> int:
    """The PreToolUse Hook of the Checks a Hook runs (ADR checks): it runs the ones the Config turns
    on, and denies the call when one would. It says nothing of input it can't read, and Claude Code
    runs the call as usual."""
    call = _tool_call(text)
    try:
        dir = hook.project()
    except OSError:
        return 0
    if call is None:
        return 0
    cwd = call.get("cwd") or dir
    if call.get("tool_name") == "Bash":
        command = (call.get("tool_input") or {}).get("command") or ""
        why = checks.no_git_hook_bypass(command)
        if why:
            return _deny(stdout, f"{names.PLUGIN}:no-git-hook-bypass: {why}{_RUN_IT_YOURSELF}")
    why = checks.no_secrets_in_context(call, cwd)
    if why:
        return _deny(stdout, f"{names.PLUGIN}:no-secrets-in-context: {why}")
    return 0


def _deny(stdout: TextIO, reason: str) -> int:
    """Prints a PreToolUse Hook's denial, with its reason, for Claude Code."""
    hook.write(stdout, {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }})
    return 0


def session_end(text: str, stdout: TextIO) -> int:
    """The SessionEnd Hook's part (ADR session-review): in a repo, it starts a Session review of
    the session that ended and returns at once. It says nothing and never fails the exit: without
    the Transcript, `claude`, or the plugin's folder or data folder, and in a Session review's own
    session, it does nothing."""
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if os.environ.get(review.ENV, "") or not data or not plugin:
        return 0
    end = hook.decode(text)
    try:
        dir = hook.project()
        if end is None:
            return 0
        session = hook.text(end, "session_id")
        transcript_path = hook.text(end, "transcript_path")
    except (OSError, hook.Mismatch):
        return 0
    root = repo.root(dir)
    if not root:
        return 0
    claude = shutil.which("claude")
    try:
        with open(transcript_path, "rb") as f:
            transcript = f.read()
    except OSError:
        return 0
    if claude:
        try:
            review.start(claude, plugin, root, data, session, transcript)
        except OSError:
            pass
    return 0


def user_prompt_submit(text: str, stdout: TextIO) -> int:
    """The UserPromptSubmit Hook's part (ADR session-review): it tells Claude of the Proposals that
    came, such as from a Session review that ended after session start, and the session hasn't
    been told of yet, and once of a newer version installed for the project, which only a restart
    runs (ADR doctor). It says nothing else, and nothing in a Session review's session.
    In a session the plugin was updated in, which no SessionStart Hook ran for, the link in the
    plugin's data folder still points at the version before (see binlink): it runs this version's
    session start first, which points it here, and says nothing of what fails there. What both
    tell goes in one JSON: Claude Code drops a Hook's output that holds two."""
    if os.environ.get(review.ENV, ""):
        return 0
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    prompt = hook.decode(text)
    try:
        session = hook.text(prompt, "session_id") if prompt is not None else ""
    except hook.Mismatch:
        session = ""
    told = io.StringIO()
    if data and os.path.realpath(os.path.join(data, names.PLUGIN)) != binlink.PLUGIN:
        if session_start.run(session, told, io.StringIO()) != 0:
            told = io.StringIO()
    if prompt is not None and session:
        lines = _prompt_lines(data, session)
        if lines:
            told.write(f"{names.PLUGIN}:\n" + "\n".join(lines) + "\n")
    if told.getvalue():
        hook.context(stdout, "UserPromptSubmit", told.getvalue())
    return 0


def _prompt_lines(data: str, session: str) -> List[str]:
    """What a prompt of the session `session` tells Claude, apart from session start."""
    try:
        dir = hook.project()
    except OSError:
        return []
    root = repo.root(dir)
    if not root:
        return []
    lines = review.show(root, data, session, hook.decide_command())
    newer = version.newer_installed(root) if not review.headless() else ""
    if newer and once.first(data, "restart", session):
        lines.append(
            f"this session runs {names.PLUGIN} {version.read()}, but {newer} is installed for this "
            "project: tell the user to restart Claude Code to run it"
        )
    return lines


def review_decision(args: List[str], stdout: TextIO, stderr: TextIO) -> int:
    """Logs the user's decision on a Proposal, the arguments `args`: its review, its id and the
    decision (ADR session-review). It fails where the decision can't be logged, saying why."""
    prefix = f"{names.PLUGIN} review-decision: "
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    root = repo.root(dir)
    if not root:
        stderr.write(f"{prefix}{dir} is not in a repo\n")
        return 1
    try:
        todo = review.decide(
            root, os.environ.get("CLAUDE_PLUGIN_DATA", ""), args[0], args[1], args[2]
        )
    except (review.Error, OSError) as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    stdout.write(f"logged {args[0]} {args[1]} {args[2]}\n")
    if todo:
        stdout.write(todo + "\n")
    return 0


def proposals(stdout: TextIO, stderr: TextIO) -> int:
    """Lists the Proposals still waiting for the user's decision, a line each, where the inbox
    skill finds those for the Inbox (ADR session-review)."""
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{names.PLUGIN} proposals: {e}\n")
        return 1
    root = repo.root(dir)
    if not root:
        stderr.write(f"{names.PLUGIN} proposals: {dir} is not in a repo\n")
        return 1
    for line in review.waiting(root, os.environ.get("CLAUDE_PLUGIN_DATA", "")):
        stdout.write(line + "\n")
    return 0


def setup_repo(add_hathi: Optional[bool], stdout: TextIO, stderr: TextIO) -> int:
    """The setup skill's run (PRD setup): it sets the repo up, printing what it changed and what
    is left for the skill and the user; where it can't, it writes nothing and says why."""
    prefix = f"{names.PLUGIN} setup: "
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    root = repo.root(dir)
    if not root:
        stderr.write(f"{prefix}{dir} is not in a repo\n")
        return 1
    try:
        result = setup.run(root, add_hathi)
    except (setup.Stop, OSError) as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    if result.changed:
        stdout.write("changed:\n" + "".join(f"  {p}\n" for p in result.changed))
    if result.removed:
        stdout.write("removed:\n" + "".join(f"  {p}\n" for p in result.removed))
    if not result.changed and not result.removed:
        stdout.write("nothing to change\n")
    if result.left:
        stdout.write("left:\n" + "".join(f"  {line}\n" for line in result.left))
    return 0


# How many lines either side of a moment condense --around shows.
_AROUND_LINES = 5


def condense_sessions(args: List[str], stdout: TextIO, stderr: TextIO) -> Optional[int]:
    """The retro skill's condense (ADR transcripts): the Transcripts of the project in the folder it
    runs in, condensed and masked. With no `args`, the latest session worth a Retro; `--last <n>`,
    the latest n; session ids or Transcript files, those; with more than one, a summary across them
    too. `<session> --around <line>` is the lines around one moment. It returns None for arguments
    it can't read."""

    def fail(why: str) -> int:
        stderr.write(f"{names.PLUGIN} condense: {why}\n")
        return 1

    try:
        cwd = os.getcwd()
    except OSError as e:
        return fail(_os_error("getwd", "", e))
    own = repo.own_folder()
    if not own:
        return fail("found neither CLAUDE_CONFIG_DIR nor a home folder")
    folder = condense.transcripts_folder(own, cwd)

    def file(session: str) -> str:
        if os.path.exists(session) or not folder:
            return session
        name = os.path.basename(session)
        if name.endswith(".jsonl"):
            name = name[: -len(".jsonl")]
        return os.path.join(folder, name + ".jsonl")

    if len(args) == 3 and args[1] == "--around":
        at = _atoi(args[2])
        if at is None:
            return None
        path = file(args[0])
        try:
            with open(path, "rb") as f:
                text = f.read()
        except OSError as e:
            return fail(_os_error("open", path, e))
        stdout.write(condense.around(text, at, _AROUND_LINES) + "\n")
        return 0
    sessions: List[condense.Session] = []
    if not args or args[0] == "--last":
        n: Optional[int] = 1
        if args:
            n = _atoi(" ".join(args[1:]))
            if n is None or n < 1:
                return None
        if folder:
            try:
                sessions = condense.latest(folder, n)
            except OSError as e:
                return fail(_os_error("open", e.filename or "", e))
        if not sessions:
            return fail(f"no sessions of {cwd} in {os.path.join(own, 'projects')}")
    else:
        for session in args:
            path = file(session)
            try:
                sessions.append(condense.read(path))
            except OSError as e:
                return fail(_os_error("open", path, e))
    parts = [s.report() for s in sessions]
    if len(sessions) > 1:
        parts.append(condense.summary(sessions))
    stdout.write("\n\n".join(parts) + "\n")
    return 0


def _atoi(s: str) -> Optional[int]:
    """`s` as Go's strconv.Atoi reads a number, or None."""
    return int(s) if re.fullmatch(r"[+-]?[0-9]+", s) else None


def _os_error(op: str, path: str, e: OSError) -> str:
    """`e` as Go words it, such as `open <path>: no such file or directory`."""
    why = (e.strerror or str(e)).lower() if e.errno else str(e)
    return f"{op} {path}: {why}" if path else f"{op}: {why}"


