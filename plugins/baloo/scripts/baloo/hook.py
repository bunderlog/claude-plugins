"""What every command a Hook runs shares: the folder it runs in, the JSON Claude Code gives it and
takes back, and the Guidelines' index."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, TextIO, Tuple

from baloo import guidelines


def project() -> str:
    """The folder Claude Code runs in: a Hook gets it as CLAUDE_PROJECT_DIR, and a command run by
    hand gets its working folder. It raises OSError where neither is there."""
    return os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()


def decode(text: str) -> Optional[Dict[str, Any]]:
    """The JSON object that starts `text`, what Claude Code gives a Hook on stdin, as Go's decoder
    reads it: what follows it is left, null is an empty object, and anything else is None."""
    try:
        value, _ = json.JSONDecoder().raw_decode(text.lstrip(" \t\r\n"))
    except ValueError:
        return None
    if value is None:
        return {}
    return value if isinstance(value, dict) else None


class Mismatch(Exception):
    """A field of what Claude Code gave of another type than the plugin's: Go's decoder failed the
    whole input on it, and the Hook said nothing."""


def text(obj: Dict[str, Any], key: str) -> str:
    """The string field `key` of `obj`: "" where it is missing or null; Mismatch where it is of
    another type."""
    value = obj.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise Mismatch(key)
    return value


def object_(obj: Dict[str, Any], key: str) -> Dict[str, Any]:
    """The object field `key` of `obj`: empty where it is missing or null; Mismatch where it is of
    another type."""
    value = obj.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Mismatch(key)
    return value


def write(out: TextIO, value: Any, escape_html: bool = False) -> None:
    """Writes `value` as one line of JSON, as Go's encoder does: compact, U+2028 and U+2029
    escaped, and with `escape_html` <, > and & too."""
    s = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    s = s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    if escape_html:
        s = s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    out.write(s + "\n")


def context(out: TextIO, event: str, text: str) -> None:
    """Writes the Hook's JSON that adds `text` to Claude's context, for the Hook of `event`."""
    write(out, {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def guideline_index(on: Dict[str, bool]) -> Tuple[str, Optional[str]]:
    """What Claude is told of the Guidelines `on`, in the plugin's folder that Claude Code gives a
    Hook as CLAUDE_PLUGIN_ROOT, for the Bash tool's shell: CLAUDE_CODE_SHELL, or the user's SHELL;
    with why it is short, or None."""
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    shell = os.environ.get("CLAUDE_CODE_SHELL", "") or os.environ.get("SHELL", "")
    index, why = guidelines.index(plugin, on, os.path.basename(shell) if shell else ".")
    if index and not plugin:
        return "", "CLAUDE_PLUGIN_ROOT is not set"
    return index, why


def decide_command() -> str:
    """The command Claude runs, in the repo, to log the user's decision on a Proposal: the
    plugin's review-decision, with the data folder it keeps the log in, as the doctor skill runs
    the plugin."""
    run = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "scripts", "run.py")
    return (
        "CLAUDE_PLUGIN_DATA='" + os.environ.get("CLAUDE_PLUGIN_DATA", "") + "' python3 -E -s '"
        + run + "' review-decision"
    )


_NAMED = {"\a": "\\a", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\v": "\\v"}


def one_line(s: str) -> str:
    """`s` with what isn't printable escaped, as Go does in a string literal, so a line that
    carries a repo's key or path stays one line: a newline in them can't start a line of its own
    that passes for the plugin's."""
    out = []
    for c in s:
        if c.isprintable():
            out.append(c)
        elif c in _NAMED:
            out.append(_NAMED[c])
        elif ord(c) < 0x20 or c == "\x7f":
            out.append(f"\\x{ord(c):02x}")
        elif ord(c) < 0x10000:
            out.append(f"\\u{ord(c):04x}")
        else:
            out.append(f"\\U{ord(c):08x}")
    return "".join(out)

