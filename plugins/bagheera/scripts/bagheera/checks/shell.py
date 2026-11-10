"""Reads a shell command for the programs it runs: enough for the Checks a Hook runs, not a full
shell."""

# cspell:ignore elif

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Program:
    """One program a shell command runs: its name without its folder, its arguments, and the
    variables assigned for it (`HUSKY=0 git …`)."""

    name: str
    args: List[str] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    # Its output goes into the next program, through a |.
    piped: bool = False


_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=", re.A)

# Programs that run the program after their own options and assignments; each maps to its options
# that take a value.
_WRAPPERS = {
    "sudo": ["-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"],
    "doas": ["-u", "-C"],
    "env": ["-u", "-C", "-S"],
    "command": [],
    "exec": ["-a"],
    "nohup": [],
    "time": [],
    "xargs": ["-I", "-L", "-n", "-P", "-s", "-d", "-E"],
}

SHELLS = ["sh", "bash", "zsh", "dash"]

# The shell's words that start a simple command and run the program after them.
_KEYWORDS = ["if", "then", "else", "elif", "while", "until", "do", "!", "{"]


def base(p: str) -> str:
    """The last element of the path `p`, as Go's path.Base: "." for "", "/" for slashes alone."""
    if not p:
        return "."
    stripped = p.rstrip("/")
    if not stripped:
        return "/"
    return stripped.rsplit("/", 1)[-1]


def programs(command: str) -> List[Program]:
    """The programs the shell command `command` runs, past keywords such as then, wrappers such as
    sudo and env, and into `eval` and `sh -c`: enough to find each program and its arguments, not a
    full shell. A for loop's header is a program named for. An env with no program after it runs
    nothing but prints the environment, so it is one."""
    found: List[Program] = []
    cmds, piped = segments(command)
    for i, words in enumerate(cmds):
        env: List[str] = []
        bare_env = False
        while words:
            if _ASSIGNMENT.search(words[0]):
                env, words = env + [words[0]], words[1:]
                continue
            if words[0] in _KEYWORDS:
                words = words[1:]
                continue
            valued = _WRAPPERS.get(base(words[0]))
            if valued is None:
                break
            bare_env = base(words[0]) == "env"
            words = words[1:]
            while words and words[0].startswith("-"):
                if words[0] in valued and len(words) > 1:
                    words = words[1:]
                words = words[1:]
        if not words:
            if bare_env:
                found.append(Program("env", [], env, piped[i]))
            continue
        name, args = base(words[0]), words[1:]
        if name == "eval":
            found += programs(" ".join(args))
        elif name in SHELLS:
            at = next((j for j, a in enumerate(args) if short_flag(a, "c")), -1)
            if 0 <= at < len(args) - 1:
                found += programs(args[at + 1])
        else:
            found.append(Program(name, args, env, piped[i]))
    return found


def split(command: str) -> List[List[str]]:
    """The words of each simple command in `command`, split on ; & | ( ) ` and newlines, with
    quotes and backslashes taken off."""
    return segments(command)[0]


@dataclass
class _Heredoc:
    """A here-document's delimiter, and whether its lines may start with tabs (<<-)."""

    delim: str = ""
    tabs: bool = False


def segments(command: str) -> Tuple[List[List[str]], List[bool]]:
    """split's commands, each with whether a single | pipes its output into the next. A
    here-document's body is text a program reads, not commands, so it is left out, but for a
    shell's."""
    cmds: List[List[str]] = [[]]
    piped = [False]
    bodies: List[_Heredoc] = []
    word: List[str] = []
    in_word = False

    def flush() -> None:
        nonlocal in_word
        if in_word:
            cmds[-1].append("".join(word))
        word.clear()
        in_word = False

    quote = ""
    s = command
    i = 0
    while i < len(s):
        c = s[i]
        if quote:
            if c == quote:
                quote = ""
            elif c == "\\" and quote == '"' and i + 1 < len(s):
                i += 1
                word.append(s[i])
            else:
                word.append(c)
        elif (
            c == "<"
            and i + 1 < len(s)
            and s[i + 1] == "<"
            and (i + 2 == len(s) or s[i + 2] != "<")
            and (i == 0 or s[i - 1] != "<")
        ):
            flush()
            h, i = _heredoc_at(s, i + 2)
            # A shell reads its here-document as commands: those are checked like any other.
            if not any(base(w) in SHELLS for w in cmds[-1]):
                bodies.append(h)
        elif c == "\n" and bodies:
            flush()
            cmds.append([])
            piped.append(False)
            i = _skip_bodies(s, i + 1, bodies) - 1
            bodies = []
        elif c in ('"', "'"):
            quote, in_word = c, True
        elif c == "\\" and i + 1 < len(s):
            i += 1
            if s[i] != "\n":  # a backslash and a newline join two lines
                word.append(s[i])
                in_word = True
        elif c in ";&|()`\n":
            flush()
            piped[-1] = (
                c == "|" and (i + 1 == len(s) or s[i + 1] != "|") and (i == 0 or s[i - 1] != "|")
            )
            cmds.append([])
            piped.append(False)
        elif c in (" ", "\t"):
            flush()
        else:
            word.append(c)
            in_word = True
        i += 1
    flush()
    kept = [(words, p) for words, p in zip(cmds, piped) if words]
    return [words for words, _ in kept], [p for _, p in kept]


def _heredoc_at(s: str, at: int) -> Tuple[_Heredoc, int]:
    """The here-document whose << ends just before `at` in `s`, and the index of the delimiter's
    last character."""
    h = _Heredoc()
    if at < len(s) and s[at] == "-":
        h.tabs, at = True, at + 1
    while at < len(s) and s[at] in (" ", "\t"):
        at += 1
    delim = []
    while at < len(s) and s[at] not in " \t\n;&|()<>":
        if s[at] not in "'\"\\":
            delim.append(s[at])
        at += 1
    h.delim = "".join(delim)
    return h, at - 1


def _skip_bodies(s: str, at: int, bodies: List[_Heredoc]) -> int:
    """The index in `s` just past the bodies of the here-documents `bodies`, which start at `at`,
    each ending at a line that is its delimiter."""
    for h in bodies:
        while at < len(s):
            end = s.find("\n", at)
            if end < 0:
                end = len(s)
            line = s[at:end]
            if h.tabs:
                line = line.lstrip("\t")
            at = end + 1
            if line == h.delim:
                break
    return min(at, len(s))


def short_flag(a: str, f: str) -> bool:
    """Whether the argument `a` is the short flag -`f`, alone or among others (`-nm`)."""
    return len(a) > 1 and a[0] == "-" and a[1] != "-" and f in a[1:]


# git's options before its subcommand that take the next argument as their value.
_GIT_VALUED = ["-C", "-c", "--git-dir", "--work-tree", "--namespace"]


def split_git(args: List[str]) -> Tuple[List[str], str, List[str]]:
    """git's arguments `args` split into the options before its subcommand, each followed by its
    value where it takes one, the subcommand, "" for none, and the subcommand's arguments."""
    options: List[str] = []
    while args and args[0].startswith("-"):
        n = 2 if args[0] in _GIT_VALUED and len(args) > 1 else 1
        options, args = options + args[:n], args[n:]
    if not args:
        return options, "", []
    return options, args[0], args[1:]


def has_flag(args: List[str], *flags: str) -> bool:
    """Whether the arguments `args` have one of the flags `flags`: a long one as it is, a short one
    alone or among others (`-f` in `-fd`)."""
    return any(
        a == f or (len(f) == 2 and f[0] == "-" and short_flag(a, f[1])) for f in flags for a in args
    )
