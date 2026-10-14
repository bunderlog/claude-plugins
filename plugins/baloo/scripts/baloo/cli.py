"""The plugin's commands, one for each part of the plugin, as its Hooks, Git hooks, Status line
and skills run them through scripts/run.py (ADR binary)."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from datetime import date
from typing import Any, Dict, List, Optional, TextIO, Tuple

from baloo import (
    binlink,
    checks,
    condense,
    config,
    doctor,
    guidelines,
    hook,
    names,
    once,
    review,
    session_start,
    settings,
    statusline,
    version,
)

USAGE = (
    "usage: baloo version | doctor | session-start [UserPromptSubmit] | allow-guideline | "
    "subagent-start | status-line |\n"
    "  pre-tool-use | post-tool-use | session-end | user-prompt-submit |\n"
    "  review-decision <review> <proposal> accepted|accepted-edited|rejected|deferred |\n  "
    + " |\n  ".join(checks.usage())
    + " |\n"
    "  git-hook " + "|".join(sorted(checks.GIT_HOOKS)) + " <git's arguments> |\n"
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
            "allow-guideline": allow_guideline,
            "subagent-start": subagent_start,
            "status-line": status_line,
            "pre-tool-use": pre_tool_use,
            "post-tool-use": post_tool_use,
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
    if args and args[0] == "condense":
        code = condense_sessions(args[1:], stdout, stderr)
        if code is not None:
            return code
    if len(args) > 1 and args[0] == "git-hook":
        code = git_hook(args[1], args[2:], stdin, stdout, stderr)
        if code is not None:
            return code
    if len(args) > 1 and args[0] == "check":
        in_, c = _git_hook_input(stdin)
        code = checks.run(args[1], args[2:], in_, c.check_on, stderr)
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
    index, _ = hook.guideline_index(config.read(dir).guidelines)
    if not index:
        return 0
    hook.write(stdout, {"hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": index,
    }}, escape_html=True)
    return 0


def status_line(text: str, stdout: TextIO) -> int:
    """Claude Code's status line command (ADR status-line): it prints the Status line for what
    Claude Code gives it on stdin, in a terminal as wide as COLUMNS says, with the bars the Config
    of the repo it shows sets, read each time so an edit shows at the next run. A field of another
    type than the plugin's is left out, and the rest shows; whatever else goes wrong, it prints
    nothing, since Claude Code shows under the prompt whatever it prints."""
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
    if in_.current_dir:
        got = config.read(in_.current_dir).status_layout
        if got is not None:
            layout = got
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
    c = config.read(dir)
    if c.check_on("no-git-hook-bypass") and call.get("tool_name") == "Bash":
        command = (call.get("tool_input") or {}).get("command") or ""
        why = checks.no_git_hook_bypass(command)
        if why:
            return _deny(stdout, f"{names.PLUGIN}:no-git-hook-bypass: {why}{_RUN_IT_YOURSELF}")
    if c.check_on("no-secrets-in-context"):
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


# How long the format-on-edit command may run, under the Hook's own limit.
_FORMAT_TIMEOUT = 50


def post_tool_use(text: str, stdout: TextIO) -> int:
    """The PostToolUse Hook on Claude's reads, edits and Bash commands, and the PostToolUseFailure
    Hook on its Bash commands. For a file in the repo, or a command, it gives Claude the Guidelines
    of its subject or its task, once a session (ADR guidelines), and after an Edit, Write or
    MultiEdit it runs the Config's format-on-edit command in the repo's root on the file (ADR
    format-on-edit), saying nothing of how that went. In a Session review's session it does
    nothing."""
    if os.environ.get(review.ENV, ""):
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
    c = config.read(dir)
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if not c.root:
        return 0
    if tool == "Bash":
        failed = event == "PostToolUseFailure"
        try:
            given = guidelines.for_command(
                plugin, data, session, command, failed, output, c.guidelines
            )
        except OSError:
            given = ""
        if given:
            hook.context(stdout, event, f"{names.PLUGIN}:\n{given}\n")
        return 0
    if not os.path.isabs(path):
        return 0
    rel = os.path.relpath(path, c.root)
    if rel == ".." or rel.startswith(".." + os.sep):
        return 0
    try:
        given = guidelines.for_file(plugin, data, session, rel, c.guidelines, tool, created)
    except OSError:
        given = ""
    if given:
        hook.context(stdout, event, f"{names.PLUGIN}:\n{given}\n")
    if not c.format_on_edit or tool == "Read":
        return 0
    try:
        subprocess.run(
            ["sh", "-c", c.format_on_edit + ' "$1"', "sh", rel], cwd=c.root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=_FORMAT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        pass
    return 0


def session_end(text: str, stdout: TextIO) -> int:
    """The SessionEnd Hook's part (ADR session-review): where the repo's Config turns the Session
    review on, it starts one of the session that ended and returns at once. It says nothing and
    never fails the exit: without the Transcript, `claude`, or the plugin's folder or data folder,
    and in a Session review's own session, it does nothing. A problem with the Config is left to
    the next session start, as there is no one to tell now."""
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
    c = config.read(dir)
    if not c.root or not c.session_review:
        return 0
    claude = shutil.which("claude")
    try:
        with open(transcript_path, "rb") as f:
            transcript = f.read()
    except OSError:
        return 0
    if claude:
        try:
            review.start(claude, plugin, c.root, data, session, transcript)
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
    session start first, which points it here, and says nothing of what fails there."""
    if os.environ.get(review.ENV, ""):
        return 0
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if data and os.path.realpath(os.path.join(data, names.PLUGIN)) != binlink.PLUGIN:
        session_start.run_hook("UserPromptSubmit", text, stdout, io.StringIO())
    prompt = hook.decode(text)
    try:
        dir = hook.project()
        if prompt is None:
            return 0
        session = hook.text(prompt, "session_id")
    except (OSError, hook.Mismatch):
        return 0
    c = config.read(dir)
    if not c.root:
        return 0
    lines = review.show(c.root, data, session, hook.decide_command())
    newer = version.newer_installed(c.root) if not review.headless() else ""
    if newer and once.first(data, "restart", session):
        lines.append(
            f"this session runs {names.PLUGIN} {version.read()}, but {newer} is installed for this "
            "project: tell the user to restart Claude Code to run it"
        )
    if lines:
        hook.context(stdout, "UserPromptSubmit", f"{names.PLUGIN}:\n" + "\n".join(lines) + "\n")
    return 0


def review_decision(args: List[str], stdout: TextIO, stderr: TextIO) -> int:
    """Logs the user's decision on a Proposal, the arguments `args`: its review, its id and the
    decision (ADR session-review). It fails where the decision can't be logged, saying why."""
    prefix = f"{names.PLUGIN} review-decision: "
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    c = config.read(dir)
    if not c.root:
        stderr.write(f"{prefix}{dir} is not in a repo\n")
        return 1
    try:
        todo = review.decide(
            c.root, os.environ.get("CLAUDE_PLUGIN_DATA", ""), args[0], args[1], args[2]
        )
    except (review.Error, OSError) as e:
        stderr.write(f"{prefix}{e}\n")
        return 1
    stdout.write(f"logged {args[0]} {args[1]} {args[2]}\n")
    if todo:
        stdout.write(todo + "\n")
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
    own = settings.own()
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


def _git_hook_input(stdin: Optional[TextIO]) -> Tuple[checks.Input, config.Config]:
    """What the Checks Git hooks run read in the repo git runs them in, with its Config; a Check
    passes everything, and no command runs, where the Config can't be read."""
    try:
        c = config.read(os.getcwd())
    except OSError:
        c = config.Config()
    return (
        checks.Input(
            dir=".", stdin=stdin, today=date.today().isoformat(), rules=c.commit_rules,
            max_file_kb=c.max_file_kb,
        ),
        c,
    )


def git_hook(
    name: str, args: List[str], stdin: Optional[TextIO], stdout: TextIO, stderr: TextIO
) -> Optional[int]:
    """Runs the Git hook `name` (ADR git-hooks): its Checks the Config turns on, then, once they all
    pass, the command the Config sets for it, with sh, git's arguments `args` as $1 on, and for
    pre-push the refs git gave on `stdin`, which linear-history reads too. It returns the exit code
    for git: the Checks', or 1 where the command fails. None where the plugin writes no such Git
    hook, or git gives none of the arguments one of its Checks takes."""
    in_, c = _git_hook_input(stdin)
    command = c.git_hook_commands.get(name, "")
    pushed: Optional[str] = None
    if name == "pre-push" and command:
        try:
            pushed = _read_strict(stdin)
        except (OSError, ValueError) as e:
            stderr.write(f"{names.PLUGIN}:{names.GIT_HOOK_COMMANDS}.{name}: {e}\n")
            return 2
        in_.stdin = io.StringIO(pushed)
    code = checks.run_hook(name, args, in_, c.check_on, stderr)
    if code is None or code != 0 or not command:
        return code
    why = _sh(["sh", "-c", command, "sh"] + args, stdin, pushed, stdout, stderr)
    if why:
        stderr.write(f"{names.PLUGIN}:{names.GIT_HOOK_COMMANDS}.{name}: {command}: {why}\n")
        return 1
    return 0


def _read_strict(stdin: Optional[TextIO]) -> str:
    return "" if stdin is None else stdin.read()


def _fileno(stream: Any) -> Optional[int]:
    try:
        return stream.fileno()
    except (AttributeError, OSError, ValueError, io.UnsupportedOperation):
        return None


def _sh(
    argv: List[str], stdin: Optional[TextIO], given: Optional[str], stdout: TextIO, stderr: TextIO
) -> str:
    """Runs `argv` with `given` on its stdin, or else `stdin`, and its output on `stdout` and
    `stderr`; it returns why it failed, as Go words it, or ""."""
    kwargs: Dict[str, Any] = {}
    if given is not None:
        kwargs["input"] = given.encode()
    elif stdin is None:
        kwargs["stdin"] = subprocess.DEVNULL
    elif _fileno(stdin) is not None:
        kwargs["stdin"] = _fileno(stdin)
    else:
        kwargs["input"] = stdin.read().encode()
    out_fd, err_fd = _fileno(stdout), _fileno(stderr)
    for stream in (stdout, stderr):
        stream.flush()
    try:
        p = subprocess.run(
            argv,
            stdout=out_fd if out_fd is not None else subprocess.PIPE,
            stderr=err_fd if err_fd is not None else subprocess.PIPE,
            **kwargs,
        )
    except OSError as e:
        return str(e)
    if out_fd is None and p.stdout:
        stdout.write(p.stdout.decode(errors="replace"))
    if err_fd is None and p.stderr:
        stderr.write(p.stderr.decode(errors="replace"))
    if p.returncode > 0:
        return f"exit status {p.returncode}"
    if p.returncode < 0:
        return "signal: " + (signal.strsignal(-p.returncode) or str(-p.returncode)).lower()
    return ""
