"""The plugin's commands, one for each part of the plugin, as its Hooks, Git hooks, Status line
and skills run them through scripts/run.py (ADR binary)."""

from __future__ import annotations

import io
import os
import re
import sys
from typing import Any, Dict, List, Optional, TextIO

from louie import (
    binlink,
    guidelines,
    hook,
    names,
    once,
    repo,
    session_start,
    version,
)

USAGE = (
    "usage: louie version | session-start [UserPromptSubmit] | allow-guideline | subagent-start |\n"
    "  post-tool-use | user-prompt-submit"
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
        if command == "session-start":
            return session_start.run_hook("SessionStart", _read(stdin), stdout, stderr)
        hooks = {
            "allow-guideline": allow_guideline,
            "subagent-start": subagent_start,
            "post-tool-use": post_tool_use,
            "user-prompt-submit": user_prompt_submit,
        }
        if command in hooks:
            return hooks[command](_read(stdin), stdout)
    # The UserPromptSubmit Hook, in a session the plugin was updated in, runs the session start no
    # SessionStart Hook ran for this version (see user_prompt_submit).
    if args == ["session-start", "UserPromptSubmit"]:
        return session_start.run_hook(args[1], _read(stdin), stdout, stderr)
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


def allow_guideline(text: str, stdout: TextIO) -> int:
    """The Read tool's PreToolUse Hook (ADR guidelines): it allows reading a Guideline file of the
    plugin without asking the user, whose own deny and ask rules still win, and says nothing of any
    other file. It never stops a Read: whatever goes wrong, it says nothing."""
    call = hook.decode(text)
    if call is None:
        return 0
    try:
        tool = hook.text(call, "tool_name")
        path = hook.text(hook.object_(call, "tool_input"), "file_path")
    except hook.Mismatch:
        return 0
    if tool != "Read" or not guidelines.readable(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), path):
        return 0
    hook.write(stdout, {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": names.PLUGIN + ": one of the plugin's own guidelines",
    }}, escape_html=True)
    return 0


def subagent_start(text: str, stdout: TextIO) -> int:
    """The SubagentStart Hook of the plugin's verifier (ADR verify): it tells the agent, which
    session start's context doesn't reach, the Guidelines the Config turns on, as session start
    names them. For another agent, or with none on, it says nothing."""
    call = hook.decode(text)
    if call is None:
        return 0
    try:
        if hook.text(call, "agent_type") != names.VERIFIER:
            return 0
        dir = hook.project()
    except (hook.Mismatch, OSError):
        return 0
    index, _ = hook.guideline_index(repo.root(dir))
    if not index:
        return 0
    hook.write(stdout, {"hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": index,
    }}, escape_html=True)
    return 0


def post_tool_use(text: str, stdout: TextIO) -> int:
    """The PostToolUse Hook on Claude's reads, edits and Bash commands, and the PostToolUseFailure
    Hook on its Bash commands. For a file in the repo, or a command, it gives Claude the Guidelines
    of its subject or its task, once a session (ADR guidelines). In a Session review's session it
    does nothing."""
    if os.environ.get(hook.REVIEW_ENV, ""):
        return 0
    call = hook.decode(text)
    try:
        dir = hook.project()
        if call is None:
            return 0
        event = hook.text(call, "hook_event_name") or "PostToolUse"
        session = hook.text(call, "session_id")
        tool = hook.text(call, "tool_name")
        given_input = hook.object_(call, "tool_input")
        path = hook.text(given_input, "file_path")
        command = hook.text(given_input, "command")
    except (OSError, hook.Mismatch):
        return 0
    # The tool's response differs from tool to tool and isn't all documented: a field of another
    # shape counts as missing.
    response = call.get("tool_response")
    response = response if isinstance(response, dict) else {}
    created = response.get("type") == "create"
    output = "\n".join(
        v for v in (call.get("error"), response.get("stdout"), response.get("stderr"))
        if isinstance(v, str)
    )
    root = repo.root(dir)
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if not root:
        return 0
    if tool == "Bash":
        failed = event == "PostToolUseFailure"
        try:
            given = guidelines.for_command(
                plugin, data, session, command, failed, output, guidelines.EVERY
            )
        except OSError:
            given = ""
        if given:
            hook.context(stdout, event, f"{names.PLUGIN}:\n{given}\n")
        return 0
    if not os.path.isabs(path):
        return 0
    rel = os.path.relpath(path, root)
    if rel == ".." or rel.startswith(".." + os.sep):
        return 0
    try:
        given = guidelines.for_file(
            plugin, data, session, rel, guidelines.EVERY, tool, created
        )
    except OSError:
        given = ""
    if given:
        hook.context(stdout, event, f"{names.PLUGIN}:\n{given}\n")
    return 0


def user_prompt_submit(text: str, stdout: TextIO) -> int:
    """The UserPromptSubmit Hook's part: it tells Claude once of a newer version installed for the
    project, which only a restart runs. It says nothing else, and nothing in a Session review's
    session.
    In a session the plugin was updated in, which no SessionStart Hook ran for, the link in the
    plugin's data folder still points at the version before (see binlink): it runs this version's
    session start first, which points it here, and says nothing of what fails there. What both
    tell goes in one JSON: Claude Code drops a Hook's output that holds two."""
    if os.environ.get(hook.REVIEW_ENV, ""):
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
    lines: List[str] = []
    newer = version.newer_installed(root) if not hook.headless() else ""
    if newer and once.first(data, "restart", session):
        lines.append(
            f"this session runs {names.PLUGIN} {version.read()}, but {newer} is installed for this "
            "project: tell the user to restart Claude Code to run it"
        )
    return lines


def _atoi(s: str) -> Optional[int]:
    """`s` as Go's strconv.Atoi reads a number, or None."""
    return int(s) if re.fullmatch(r"[+-]?[0-9]+", s) else None


def _os_error(op: str, path: str, e: OSError) -> str:
    """`e` as Go words it, such as `open <path>: no such file or directory`."""
    why = (e.strerror or str(e)).lower() if e.errno else str(e)
    return f"{op} {path}: {why}" if path else f"{op}: {why}"


