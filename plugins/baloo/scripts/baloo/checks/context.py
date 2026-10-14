"""The Check no-secrets-in-context."""

# cspell:ignore netrc fgrep hexdump

from __future__ import annotations

import os
import re
from typing import List, Tuple

from baloo.checks.secrets import ALLOW_SECRET, is_env_file
from baloo.checks.shell import Program, has_flag, programs, split, split_git

_KEY_FILE = re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)[^/]*\Z|\.(pem|key)\Z")
# A part of a variable's name that says it holds a Secret: API_KEY, GITHUB_TOKEN, DB_PASSWORD…
_SECRET_PART = re.compile(
    r"\w*KEY|\w*TOKEN|\w*SECRET|PASSWORD|PASSWD|PASS|CREDENTIALS?|PAT", re.A
)
# A variable whose value the shell puts in: not `${NAME:+word}`, which puts in the word.
_VARIABLE = re.compile(r"\$(?:\{([A-Za-z_]\w*)(?!\w|:?\+)|([A-Za-z_]\w*))", re.A)
_HOME = re.compile(r"^(~|\$HOME|\$\{HOME\})(/|\Z)")

# Files that hold Secrets, by their path from the home folder or any other.
_SECRET_FILES = [".aws/credentials", ".netrc", ".docker/config.json", ".config/gh/hosts.yml"]

# Programs that show a file's contents.
_READERS = [
    "cat", "bat", "less", "more", "head", "tail", "tac", "nl", "grep", "egrep", "fgrep", "rg",
    "ag", "sed", "awk", "cut", "sort", "uniq", "strings", "xxd", "od", "hexdump", "base64", "jq",
    "yq", "diff", "column", "view",
]
# Readers whose first argument is a pattern or a script, not a file, unless it is given with an
# option.
_PATTERN_FIRST = ["grep", "egrep", "fgrep", "rg", "ag", "sed", "awk", "jq", "yq"]

_MARK_ADVICE = (
    f"only the user marks an env file as holding no secrets ({ALLOW_SECRET}). If it really holds "
    "none, ask the user to mark it themselves."
)


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def no_secrets_in_context(call: dict, dir: str) -> str:
    """The Check baloo:no-secrets-in-context (PreToolUse on Bash, Read, Grep, Edit, Write and
    MultiEdit): why the tool call `call`, Claude Code's PreToolUse input with its tool_name and
    tool_input, run in the folder `dir`, would Leak a Secret into Claude's context, or mark an Env
    file as holding none, which only the user does; "" when it would do neither. It says so to
    Claude, with what to ask the user instead."""
    tool = _str(call.get("tool_name"))
    given = call.get("tool_input")
    given = given if isinstance(given, dict) else {}
    edits = given.get("edits")
    written = [_str(given.get("content")), _str(given.get("new_string"))] + [
        _str(e.get("new_string")) for e in (edits if isinstance(edits, list) else [])
        if isinstance(e, dict)
    ]
    why = ""
    if tool == "Bash":
        command = _str(given.get("command"))
        if _marks(command):
            return _MARK_ADVICE
        why = _leak(command, dir)
    elif tool == "Read":
        why = _secret_file(_str(given.get("file_path")), dir)
    elif tool == "Grep":
        why = _secret_file(_str(given.get("path")), dir) or _secret_file(
            _str(given.get("glob")), dir
        )
    elif tool in ("Edit", "Write", "MultiEdit"):
        if is_env_file(_str(given.get("file_path"))) and any(ALLOW_SECRET in w for w in written):
            return _MARK_ADVICE
    if not why:
        return ""
    return (
        why + ": showing it would put a secret into this session. If it's really needed, ask the "
        "user to look in their own terminal, not with `!`, whose output enters the session."
    )


def _leak(command: str, dir: str) -> str:
    """Why the shell command `command`, run in `dir`, would show a Secret, or "" when it wouldn't:
    the first of its programs that would, but an env whose pipeline keeps only the names."""
    found = programs(command)
    for i, p in enumerate(found):
        why = _shows(p, dir)
        if why and not (_dumps_env(p) and _keeps_names(found[i:])):
            return why
    return ""


def _substituted(arg: str) -> Tuple[str, List[str]]:
    """The argument `arg` without its command substitutions, `$(…)`, and the commands they run:
    what a program is given in their place is their output, not their text."""
    kept: List[str] = []
    inner: List[str] = []
    i = 0
    while i < len(arg):
        if arg.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(arg) and depth:
                depth += {"(": 1, ")": -1}.get(arg[j], 0)
                j += 1
            inner.append(arg[i + 2 : j - 1] if depth == 0 else arg[i + 2 :])
            i = j
        else:
            kept.append(arg[i])
            i += 1
    return "".join(kept), inner


def _marks(command: str) -> bool:
    """Whether the shell command `command` would write ALLOW_SECRET into an Env file: it names
    both."""
    if ALLOW_SECRET not in command:
        return False
    return any(is_env_file(w.lstrip("<>")) for words in split(command) for w in words)


def _secret_file(path: str, dir: str) -> str:
    """Why showing the file at `path`, from the folder `dir`, would Leak a Secret, or "" when it
    wouldn't. An Env file with ALLOW_SECRET on its first line holds none; one that can't be read
    counts as unmarked."""
    if not path:
        return ""
    p = path
    if _HOME.search(p):
        home = os.path.expanduser("~")
        if home != "~":
            p = _HOME.sub(lambda m: home + m[2], p)
    if is_env_file(p):
        if not os.path.isabs(p):
            p = os.path.join(dir, p)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                first = f.readline()
        except OSError:
            first = ""
        return "" if ALLOW_SECRET in first else path + " is an env file"
    if _KEY_FILE.search(p) and not p.endswith(".pub"):
        return path + " holds a private key"
    if any(p == f or p.endswith("/" + f) for f in _SECRET_FILES):
        return path + " holds secrets"
    return ""


def _shows(p: Program, dir: str) -> str:
    """Why the program `p`, run in `dir`, would show a Secret, or "" when it wouldn't: a file one
    of the readers shows, or redirected into any program (`… < .env`), or a Secret it prints
    itself."""
    args = p.args
    pattern = -1
    with_option = has_flag(args, "-e", "-f", "--regexp", "--file", "--expression")
    if p.name in _PATTERN_FIRST and not with_option:
        pattern = next((i for i, a in enumerate(args) if not a.startswith("-")), -1)
    for i, a in enumerate(args):
        file = ""
        if a.startswith("<"):
            file = a[1:]
            if not file and i + 1 < len(args):
                file = args[i + 1]
        elif p.name in _READERS and i != pattern:
            file = a
        why = _secret_file(file, dir)
        if why:
            return why
    named = [a for a in args if not a.startswith("-")]

    def secret(names: List[str]) -> str:
        return next((n for n in names if _secret_name(n)), "")

    if p.name in ("env", "printenv"):
        if _dumps_env(p):
            return p.name + " prints every environment variable"
        s = secret(named)
        if p.name == "printenv" and s:
            return f"printenv {s} prints a secret"
    elif p.name in ("export", "declare", "typeset"):
        if not named:
            return p.name + " prints every exported variable"
        s = secret(named)
        if has_flag(args, "-p") and s:
            return f"{p.name} -p {s} prints a secret"
    elif p.name == "set":
        if not args:
            return "set prints every shell variable"
    elif p.name in ("echo", "printf", "print"):
        shown: List[str] = []
        for a in args:
            text, inner = _substituted(a)
            why = next((w for w in (_leak(c, dir) for c in inner) if w), "")
            if why:
                return why
            shown.append(text)
        s = secret([m[1] or m[2] for a in shown for m in _VARIABLE.finditer(a)])
        if s:
            return f"{p.name} ${s} prints a secret"
    elif p.name == "gh":
        if (
            len(args) > 1
            and args[0] == "auth"
            and (
                args[1] == "token"
                or (args[1] == "status" and has_flag(args, "--show-token", "-t"))
            )
        ):
            return "gh auth token prints a secret"
    elif p.name == "security":
        if (
            args
            and args[0] in ("find-generic-password", "find-internet-password")
            and has_flag(args, "-w", "-g")
        ):
            return f"security {args[0]} -w prints a password"
    elif p.name == "aws":
        if (
            len(args) > 1
            and args[0] == "configure"
            and (
                args[1] == "export-credentials"
                or (args[1] == "get" and len(args) > 2 and _secret_name(args[2]))
            )
        ):
            return f"aws configure {args[1]} prints a secret"
    elif p.name == "op":
        if args and args[0] == "read":
            return "op read prints a secret"
    elif p.name == "git":
        _, sub, rest = split_git(args)
        if sub == "credential" and rest and rest[0] == "fill":
            return "git credential fill prints a secret"
    return ""


def _dumps_env(p: Program) -> bool:
    """Whether the program `p` prints every environment variable: env or printenv without a
    name."""
    return p.name in ("env", "printenv") and all(a.startswith("-") for a in p.args)


def _keeps_names(p: List[Program]) -> bool:
    """Whether a later program of the pipeline that starts at `p[0]` keeps only the variables'
    names of what it is given, as `cut -d= -f1` does."""
    i = 0
    while i + 1 < len(p) and p[i].piped:
        if _names_only(p[i + 1]):
            return True
        i += 1
    return False


# A grep -o pattern that can match only the start of a line, and no `=`.
_NAME_MATCH = re.compile(r"\^[\w()|\[\]*+?{},-]*", re.A)
_CUT_NAMES = re.compile(r"-d ?= -f ?1|-f ?1 -d ?=")
_AWK_NAMES = re.compile(r"-F ?= \{ ?print \$1 ?\}")


def _names_only(p: Program) -> bool:
    """Whether the program `p` prints only what comes before each line's first `=`."""
    args = " ".join(p.args)
    if p.name == "cut":
        return bool(_CUT_NAMES.fullmatch(args))
    if p.name == "awk":
        return bool(_AWK_NAMES.fullmatch(args))
    if p.name == "sed":
        script = args.removeprefix("-E ").removeprefix("-e ").strip()
        if len(script) < 2 or script[0] != "s":
            return False
        parts = script[2:].split(script[1])
        return (
            len(parts) == 3
            and parts[0] == "=.*"
            and not any(c in parts[1] for c in "&\\")
            and parts[2] in ("", "g")
        )
    if p.name == "grep":
        patterns = [a for a in p.args if not a.startswith("-")]
        return (
            (has_flag(p.args, "-o") or "--only-matching" in p.args)
            and len(patterns) == 1
            and all(_NAME_MATCH.fullmatch(a) for a in _alternatives(patterns[0]))
        )
    return False


def _alternatives(pattern: str) -> List[str]:
    """The grep pattern `pattern` split on its `|` and `\\|` outside parentheses: each of them
    matches on its own."""
    found = [""]
    depth = 0
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if depth == 0 and (c == "|" or pattern.startswith("\\|", i)):
            found.append("")
            i += 1 if c == "|" else 2
            continue
        depth += {"(": 1, ")": -1}.get(c, 0)
        found[-1] += c
        i += 1
    return found


def _secret_name(name: str) -> bool:
    """Whether the variable's name `name` says it holds a Secret."""
    return any(
        _SECRET_PART.fullmatch(part) for part in re.split(r"[_.\-]", name.upper()) if part
    )
