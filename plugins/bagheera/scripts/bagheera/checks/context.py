"""The Check no-secrets-in-context."""

# cspell:ignore netrc fgrep hexdump

from __future__ import annotations

import glob
import os
import re
from typing import Callable, Dict, List, Tuple

from bagheera.checks.secrets import ALLOW_SECRET, is_env_file
from bagheera.checks.shell import Program, base, has_flag, programs, split, split_git

_KEY_FILE = re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)[^/]*\Z|\.(pem|key)\Z")
# A name that says the key is public: `id_ed25519.pub`, `cgs.pub.mock.pem`, `server-public.pem`.
_PUBLIC_KEY = re.compile(r"(^|[._-])pub(lic)?([._-]|\Z)")
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
    "yq", "diff", "column", "view", "rev", "paste", "fold", "fmt", "pr", "expand", "unexpand",
    "iconv", "comm", "join",
]
# Readers whose first argument is a pattern or a script, not a file, unless it is given with an
# option.
_PATTERN_FIRST = ["grep", "egrep", "fgrep", "rg", "ag", "sed", "awk", "jq", "yq"]
# jq's options that take a name and a value before its program (`--arg p "$p"`).
_JQ_PAIRS = ["--arg", "--argjson", "--slurpfile", "--rawfile"]
# Interpreters, each with its options whose value is code it runs: a file that code names in
# quotes, `open(".env")`, it most likely reads.
_INLINE_CODE = {
    "python": ["-c"], "python3": ["-c"], "node": ["-e", "--eval", "-p", "--print"],
    "bun": ["-e", "--eval", "-p", "--print"], "deno": ["eval"], "perl": ["-e", "-E"],
    "ruby": ["-e"], "php": ["-r"],
}
_QUOTED = re.compile(r"([\"'`])([^\"'`]+)\1")
# The characters that make a path a pattern the shell expands.
_GLOB = re.compile(r"[*?\[]")

_MARK_ADVICE = (
    f"only the user marks an env file as holding no secrets ({ALLOW_SECRET}). If it really holds "
    "none, ask the user to mark it themselves."
)


def _str(value) -> str:
    return value if isinstance(value, str) else ""


def no_secrets_in_context(call: dict, dir: str) -> str:
    """The Check no-secrets-in-context (PreToolUse on Bash, Read, Grep, Edit, Write and
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
    the first of its programs that would, but an env whose pipeline keeps only the names, and a
    command whose output a variable takes, unless an echo or a printf then prints that variable."""
    command, held = _captured(command, dir)
    found = programs(command)
    for i, p in enumerate(found):
        why = _shows(p, dir) or _prints_held(p, held)
        if why and not (_dumps_env(p) and _keeps_names(found[i:])):
            return why
    return ""


# A variable assigned a command's output, `T=$(…)` or `T="$(…)"`, at the start of a word.
_CAPTURE = re.compile(r"(?:^|(?<=[\s;&|(]))([A-Za-z_]\w*)=\"?\$\(", re.A)


def _captured(command: str, dir: str) -> Tuple[str, Dict[str, str]]:
    """The shell command `command` without the command substitutions whose output a variable
    takes, and why each such variable, run in `dir`, holds a Secret: the output is the variable's,
    not the context's, until something prints it."""
    held: Dict[str, str] = {}
    while True:
        m = _CAPTURE.search(command)
        if not m:
            return command, held
        start = m.end() - 2
        depth, j = 1, m.end()
        while j < len(command) and depth:
            depth += {"(": 1, ")": -1}.get(command[j], 0)
            j += 1
        why = _leak(command[m.end() : j - 1], dir)
        if why:
            held[m[1]] = why
        command = command[:start] + command[j:]


def _prints_held(p: Program, held: Dict[str, str]) -> str:
    """Why the program `p` prints a variable that holds a Secret, `held` by name, or ""."""
    if not held or p.name not in ("echo", "printf", "print") or _to_file(p.args):
        return ""
    names = [m[1] or m[2] for a in p.args for m in _VARIABLE.finditer(a)]
    return next((held[n] for n in names if n in held), "")


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
    # A pattern that reads as a Secret's file, *.env or *.pem, is one wherever it matches, as a
    # Grep's glob is; another shows each file the shell expands it to: .e* matches .env, * doesn't.
    why = _secret_path(path, p, dir)
    if why or not _GLOB.search(p):
        return why
    absolute = os.path.isabs(p)
    for m in sorted(glob.glob(p if absolute else os.path.join(glob.escape(dir), p))):
        shown = m if absolute else os.path.relpath(m, dir)
        why = _secret_path(shown, m, dir)
        if why:
            return why
    return ""


def _secret_path(path: str, p: str, dir: str) -> str:
    """_secret_file's answer for the file `path`, `p` once its home folder is expanded."""
    if is_env_file(p):
        if not os.path.isabs(p):
            p = os.path.join(dir, p)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                first = f.readline()
        except OSError:
            first = ""
        return "" if ALLOW_SECRET in first else path + " is an env file"
    if _KEY_FILE.search(p) and not _PUBLIC_KEY.search(base(p)):
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
        values = 0
        for i, a in enumerate(args):
            if values:
                values -= 1
            elif p.name in ("jq", "yq") and a in _JQ_PAIRS:
                values = 2
            elif not a.startswith("-"):
                pattern = i
                break
    for i, a in enumerate(args):
        file = ""
        if a.startswith("<"):
            file = a[1:]
            if not file and i + 1 < len(args):
                file = args[i + 1]
        elif p.name in _READERS and i != pattern and not a.startswith("-"):
            file = a
        why = _secret_file(file, dir)
        if why and not _hides_values(p, i):
            return why
    show = _PRINTERS.get(p.name)
    if show is not None:
        return show(p, dir)
    if p.name in _INLINE_CODE:
        return _inline_code(p, dir)
    return ""


def _named(args: List[str]) -> List[str]:
    return [a for a in args if not a.startswith("-")]


def _secret_named(names: List[str]) -> str:
    """The first of the variables' names `names` that says it holds a Secret, or ""."""
    return next((n for n in names if _secret_name(n)), "")


def _env(p: Program, dir: str) -> str:
    if _dumps_env(p):
        return p.name + " prints every environment variable"
    s = _secret_named(_named(p.args))
    return f"printenv {s} prints a secret" if p.name == "printenv" and s else ""


def _export(p: Program, dir: str) -> str:
    named = _named(p.args)
    if not named:
        return p.name + " prints every exported variable"
    s = _secret_named(named)
    return f"{p.name} -p {s} prints a secret" if has_flag(p.args, "-p") and s else ""


def _set(p: Program, dir: str) -> str:
    return "" if p.args else "set prints every shell variable"


def _echo(p: Program, dir: str) -> str:
    if _to_file(p.args):
        return ""
    shown: List[str] = []
    for a in p.args:
        text, inner = _substituted(a)
        why = next((w for w in (_leak(c, dir) for c in inner) if w), "")
        if why:
            return why
        shown.append(text)
    s = _secret_named([m[1] or m[2] for a in shown for m in _VARIABLE.finditer(a)])
    return f"{p.name} ${s} prints a secret" if s else ""


def _gh(p: Program, dir: str) -> str:
    args = p.args
    if len(args) > 1 and args[0] == "auth" and (
        args[1] == "token" or (args[1] == "status" and has_flag(args, "--show-token", "-t"))
    ):
        return "gh auth token prints a secret"
    return ""


def _security(p: Program, dir: str) -> str:
    args = p.args
    if (
        args
        and args[0] in ("find-generic-password", "find-internet-password")
        and has_flag(args, "-w", "-g")
    ):
        return f"security {args[0]} -w prints a password"
    return ""


def _aws(p: Program, dir: str) -> str:
    args = p.args
    if len(args) > 1 and args[0] == "configure" and (
        args[1] == "export-credentials"
        or (args[1] == "get" and len(args) > 2 and _secret_name(args[2]))
    ):
        return f"aws configure {args[1]} prints a secret"
    return ""


def _op(p: Program, dir: str) -> str:
    return "op read prints a secret" if p.args and p.args[0] == "read" else ""


def _git(p: Program, dir: str) -> str:
    _, sub, rest = split_git(p.args)
    if sub == "credential" and rest and rest[0] == "fill":
        return "git credential fill prints a secret"
    return ""


# The programs that print a Secret themselves, each with why it does, or "" when it doesn't.
_PRINTERS: Dict[str, Callable[[Program, str], str]] = {
    "env": _env, "printenv": _env, "export": _export, "declare": _export, "typeset": _export,
    "set": _set, "echo": _echo, "printf": _echo, "print": _echo, "gh": _gh,
    "security": _security, "aws": _aws, "op": _op, "git": _git,
}


def _inline_code(p: Program, dir: str) -> str:
    """Why the code the interpreter `p` is given to run, not a script's file, would show a Secret:
    a file it names in quotes holds one."""
    options = _INLINE_CODE[p.name]
    for i, a in enumerate(p.args[:-1]):
        if a in options:
            for m in _QUOTED.finditer(p.args[i + 1]):
                why = _secret_file(m[2], dir)
                if why:
                    return why
    return ""


_GREPS = ("grep", "egrep", "fgrep")
# grep's flags that print no line: a count, the files' names, or nothing.
_NO_LINES = (
    "-c", "-l", "-L", "-q", "--count", "--files-with-matches", "--files-without-match", "--quiet",
    "--silent",
)


def _hides_values(p: Program, at: int) -> bool:
    """Whether the program `p` shows no value of the file its argument at `at` names: a grep that
    prints only a count or the files' names, or only the names before `=`. Another reader, as
    `cut -d= -f1`, prints a line with no `=` whole, as the next line of a value over several is."""
    if p.name not in _GREPS:
        return False
    drop = 2 if p.args[at] == "<" else 1
    rest = Program(p.name, p.args[:at] + p.args[at + drop :])
    return has_flag(p.args, *_NO_LINES) or _names_only(rest)


# A redirection of the output, `>` or `>>`, with its target when it is in the same word.
_REDIRECT = re.compile(r"1?>>?(.*)", re.S)


def _to_file(args: List[str]) -> bool:
    """Whether the arguments `args` send the program's output into a file: not into a descriptor,
    as `>&2` (whose `&` ends the word), or a device other than /dev/null."""
    for i, a in enumerate(args):
        m = _REDIRECT.fullmatch(a)
        if not m:
            continue
        target = m[1] or (args[i + 1] if i + 1 < len(args) else "")
        if target and (target == "/dev/null" or not target.startswith("/dev/")):
            return True
    return False


def _dumps_env(p: Program) -> bool:
    """Whether the program `p` prints every environment variable: env or printenv without a
    name."""
    return p.name in ("env", "printenv") and all(a.startswith("-") for a in p.args)


def _keeps_names(p: List[Program]) -> bool:
    """Whether a later program of the pipeline that starts at `p[0]` keeps only the variables'
    names of what it is given, as `cut -d= -f1` does, or prints no line of it, as `grep -c`."""
    i = 0
    while i + 1 < len(p) and p[i].piped:
        n = p[i + 1]
        if _names_only(n) or (n.name in _GREPS and has_flag(n.args, *_NO_LINES)):
            return True
        i += 1
    return False


# A grep -o pattern that can match only the start of a line, and no `=` but one at its end.
_NAME_MATCH = re.compile(r"\^[\w()|\[\]*+?{},-]*=?", re.A)
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
        # The pattern is the first word but a flag, where no -e or -f gives it: the rest are files.
        words = [a for a in p.args if not a.startswith("-")]
        return (
            (has_flag(p.args, "-o") or "--only-matching" in p.args)
            and not has_flag(p.args, "-e", "-f", "--regexp", "--file")
            and len(words) >= 1
            and all(_NAME_MATCH.fullmatch(a) for a in _alternatives(words[0]))
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
