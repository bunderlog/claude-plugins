"""The Check conventional-commits."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from baloo.checks.coauthor import SCISSORS

# A letter or a digit is `[^\W_]`: Python's re has no \p{L} or \p{N}.
_SUBJECT = re.compile(r"^[^\W_](?:[^\W_]|-)*(\([^()\n]*[^()\s][^()\n]*\))?!?: \S")
_HEADER = re.compile(r"^([^(!:]*)(?:\([^()]*\))?!?: (.*)$")
_QUOTED = re.compile(r"`[^`]*`|\"[^\"]*\"|'[^']*'")
_LETTER = re.compile(r"^[a-zA-Z]")
# A footer's word token (`-` for spaces; BREAKING CHANGE the one exception) and its separator.
_FOOTER = re.compile(r"^((?:[^\W_]|-)+|BREAKING CHANGE)(: | #)")
_BREAKING = re.compile(r"breaking[ -]change", re.I)
# A message git, or a pull request's merge, writes itself.
_BY_GIT = re.compile(
    r"^Merge (branch|branches|remote-tracking branch|tag|commit|pull request) |"
    r'^(Revert|Reapply) "|^(fixup|squash|amend)! '
)
_NEWLINE = re.compile(r"\r?\n")
_PARAGRAPH = re.compile(r"\n\s*\n")

# config-conventional's types.
COMMIT_TYPES = [
    "build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor", "revert", "style", "test",
]

# config-conventional's longest line in a commit message, in characters.
MAX_LINE = 100


@dataclass
class CommitRules:
    """conventional-commits' settings; the default is config-conventional's."""

    # The types a subject may have: None for config-conventional's; any with any_type.
    types: Optional[List[str]] = None
    any_type: bool = False
    # The longest line, in characters: None for 100, 0 for no limit.
    max_length: Optional[int] = None


def conventional_commit(message: str, rules: CommitRules) -> str:
    """The Check baloo:conventional-commits (commit-msg): why the commit message isn't a
    Conventional Commit as commitlint's config-conventional reads it (its error rules), or "" when
    it is. That is a `type(scope)!: description` subject with one of its types, a description not
    starting in uppercase (quoted text aside) nor ending in `.`, a trimmed header, a body after a
    blank line, lines of up to 100 characters, and a breaking change footer as
    `BREAKING CHANGE: description`, in uppercase (its synonym `BREAKING-CHANGE` too). Footers are
    the trailing paragraphs that open with one. A message git writes itself, such as a merge's,
    passes. `rules` may change the types and the longest line."""
    types = COMMIT_TYPES if rules.types is None else rules.types
    longest = MAX_LINE if rules.max_length is None else rules.max_length
    lines = [
        line
        for line in _NEWLINE.split(SCISSORS.split(message, 1)[0])
        if not line.startswith("#")
    ]
    start = next((i for i, line in enumerate(lines) if line.strip()), -1)
    if start < 0 or _BY_GIT.search(lines[start]):
        return ""
    lines = lines[start:]
    s = lines[0]
    if not _SUBJECT.search(s):
        return f'"{s}" is not `type(scope): description`'
    m = _HEADER.search(s)
    kind, description = m[1], m[2]
    if not rules.any_type and kind not in types:
        return f'"{kind}" is not one of {", ".join(types)}'
    # Quoted text, such as `README`, may be in uppercase; a description that opens with it too.
    first = _QUOTED.sub("", description).strip()[:1]
    if _LETTER.search(description) and first.isupper():
        return f'"{description}" starts with an uppercase letter'
    if description.endswith("."):
        return f'"{description}" ends with a full stop'
    if s != s.strip():
        return f'"{s}" has trailing spaces'
    if len(lines) > 1 and lines[1].strip():
        return f'leave a blank line between "{s}" and the body'
    for line in lines:
        if longest > 0 and len(line) > longest:
            return f'"{line[:40]}…" is {len(line)} characters, over {longest}'
    paragraphs = _PARAGRAPH.split("\n".join(lines[1:]).strip())
    footers: List[str] = []
    for p in reversed(paragraphs):
        if not _FOOTER.search(p):
            break  # the body
        footers += p.split("\n")
    for line in footers:
        m = _FOOTER.search(line)
        if (
            m
            and _BREAKING.fullmatch(m[1])
            and (m[1] != m[1].upper() or m[2] != ": ")
        ):
            return f'"{line}" is not `BREAKING CHANGE: description`'
    return ""
