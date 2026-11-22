"""The Check no-hidden-characters."""

from __future__ import annotations

import unicodedata
from typing import List, Tuple

# The tag characters, and WAVING BLACK FLAG, which a run of them follows in the flags of England,
# Scotland and Wales: a run after it is an emoji, not hidden text.
_TAGS = (0xE0000, 0xE0080)
_FLAG = 0x1F3F4

# Characters a terminal, an editor and a diff don't show, which real text doesn't need (PRD
# hidden-characters): the bidi embeddings, overrides and isolates (Trojan Source), zero width
# space, word joiner, zero width no-break space, and the tag characters. ZWJ, ZWNJ, LRM and RLM
# are left out: emoji sequences and Persian, Hebrew and Arabic text use them.
_HIDDEN = frozenset(
    [0x200B, 0x2060, 0xFEFF]
    + list(range(0x202A, 0x202F))
    + list(range(0x2066, 0x206A))
    + list(range(_TAGS[0], _TAGS[1]))
)


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def no_hidden_characters(call: dict) -> str:
    """The Check no-hidden-characters (PreToolUse on Bash, Edit, Write and MultiEdit): why the tool
    call `call`, Claude Code's PreToolUse input, would write a character a person can't see, or ""
    when it wouldn't. An edit counts only for what its new text holds more of than its old, so it
    can remove such a character or keep one already there; a Write may start with a byte order
    mark."""
    tool = _str(call.get("tool_name"))
    given = call.get("tool_input")
    given = given if isinstance(given, dict) else {}
    if tool == "Bash":
        return _why("the command", _str(given.get("command")), "", 0)
    if tool == "Write":
        content = _str(given.get("content"))
        return _why("the Write", content, "", 1 if content.startswith("\ufeff") else 0)
    if tool == "Edit":
        return _why("the Edit", _str(given.get("new_string")), _str(given.get("old_string")), 0)
    if tool == "MultiEdit":
        edits = given.get("edits")
        for e in edits if isinstance(edits, list) else []:
            if isinstance(e, dict):
                why = _why("the MultiEdit", _str(e.get("new_string")), _str(e.get("old_string")), 0)
                if why:
                    return why
    return ""


def _why(what: str, new: str, old: str, start: int) -> str:
    """Why `new`, replacing `old`, adds a hidden character from index `start` on, or ""."""
    for at in range(start, len(new)):
        c = new[at]
        if ord(c) in _HIDDEN and new.count(c) > old.count(c) and not _in_flag(new, at):
            line, column = _place(new, at)
            return (
                f"{what} holds U+{ord(c):04X} {unicodedata.name(c, 'a hidden character')} at line "
                f"{line}, column {column}, which a person can't see in a terminal or a diff. If "
                f"it's meant, write it as an escape, such as {_escape(c)}."
            )
    return ""


def _in_flag(text: str, at: int) -> bool:
    """Whether index `at` of `text` is in a run of tag characters that follows a flag."""
    if not _TAGS[0] <= ord(text[at]) < _TAGS[1]:
        return False
    while at > 0 and _TAGS[0] <= ord(text[at - 1]) < _TAGS[1]:
        at -= 1
    return at > 0 and ord(text[at - 1]) == _FLAG


def _place(text: str, at: int) -> Tuple[int, int]:
    """The line and column, each from 1, of index `at` in `text`."""
    before: List[str] = text[:at].split("\n")
    return len(before), len(before[-1]) + 1


def _escape(c: str) -> str:
    return f"\\u{ord(c):04x}" if ord(c) <= 0xFFFF else f"\\U{ord(c):08x}"
