"""The Checks, each a function of what git or Claude Code gives the Git hook or the Hook that runs
it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, TextIO

from baloo import names
from baloo.checks.adr import no_stale_adr_date
from baloo.checks.bypass import no_git_hook_bypass
from baloo.checks.coauthor import no_ai_coauthor
from baloo.checks.commit import CommitRules, conventional_commit
from baloo.checks.conflict import no_conflict_markers
from baloo.checks.context import no_secrets_in_context
from baloo.checks.git import Error
from baloo.checks.history import linear_history
from baloo.checks.secrets import ALLOW_SECRET, mask_secrets, no_secrets_in_commits
from baloo.checks.size import DEFAULT_MAX_FILE_KB, no_large_files

__all__ = [
    "ALLOW_SECRET", "DEFAULT_MAX_FILE_KB", "GIT_HOOKS", "GIT_HOOK_CHECKS", "HOOK_CHECKS",
    "CommitRules", "Error", "Input", "conventional_commit", "linear_history", "mask_secrets",
    "no_ai_coauthor", "no_conflict_markers", "no_git_hook_bypass", "no_large_files",
    "no_secrets_in_commits", "no_secrets_in_context", "no_stale_adr_date", "run", "run_hook",
    "usage",
]


@dataclass
class Input:
    """What the Checks Git hooks run read besides git's arguments: the repo, git's stdin, today's
    date, conventional-commits' settings and no-large-files' limit."""

    dir: str = ""
    stdin: Optional[TextIO] = None
    today: str = ""  # YYYY-MM-DD
    rules: CommitRules = field(default_factory=CommitRules)
    max_file_kb: int = 0  # 0 for DEFAULT_MAX_FILE_KB


@dataclass
class _GitHookCheck:
    """A Check a Git hook runs: what it finds in the Input and the one argument it takes, if any,
    and what it tells the user to do about it."""

    name: str
    hook: str
    find: Callable[[Input, str], List[str]]
    arg: str = ""  # the argument it takes, "" for none
    stdin: str = ""  # what it reads on stdin, "" for nothing
    advice: str = ""  # the line before what it found, "" to show that alone


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            return f.read()
    except OSError as e:
        why = e.strerror or str(e)
        raise Error(f"open {path}: {why[:1].lower()}{why[1:]}") from e


def _conventional(in_: Input, path: str) -> List[str]:
    why = conventional_commit(_read(path), in_.rules)
    return [why] if why else []


# The Checks Git hooks run, in the order each Git hook runs its own.
_GIT_HOOK_CHECKS = [
    _GitHookCheck(
        "no-ai-coauthor", "commit-msg", lambda _, path: no_ai_coauthor(_read(path)),
        arg="<message file>", advice="remove the AI co-author or credit",
    ),
    _GitHookCheck("conventional-commits", "commit-msg", _conventional, arg="<message file>"),
    _GitHookCheck(
        "no-secrets-in-commits", "pre-commit", lambda in_, _: no_secrets_in_commits(in_.dir),
        advice="remove each secret, or mark a false alarm with " + ALLOW_SECRET,
    ),
    _GitHookCheck(
        "no-stale-adr-date", "pre-commit", lambda in_, _: no_stale_adr_date(in_.dir, in_.today),
        advice="an ADR's Date is when it last changed",
    ),
    _GitHookCheck(
        "no-conflict-markers", "pre-commit", lambda in_, _: no_conflict_markers(in_.dir),
        advice="resolve each conflict, or give a file that holds markers on purpose a longer "
        "conflict-marker-size in .gitattributes; conflict markers",
    ),
    _GitHookCheck(
        "no-large-files", "pre-commit", lambda in_, _: no_large_files(in_.dir, in_.max_file_kb),
        advice="keep each out of git, or raise no-large-files' max-size in " + names.CONFIG,
    ),
    _GitHookCheck(
        "linear-history", "pre-push",
        lambda in_, _: linear_history(in_.dir, in_.stdin.read() if in_.stdin else ""),
        stdin="<pushed refs>",
        advice="rebase instead of merging, then push the rebased branch with --force-with-lease; "
        "git config pull.rebase true makes git pull rebase; merge commits",
    ),
]

# The Checks Git hooks run, by name: each is off without its key under git-hooks in the Config.
GIT_HOOK_CHECKS = [c.name for c in _GIT_HOOK_CHECKS]

# The Checks a Hook runs, by name: each is on without its key under claude-hooks in the Config
# (ADR checks).
HOOK_CHECKS = ["no-git-hook-bypass", "no-secrets-in-context"]

# The Git hooks the plugin writes (ADR git-hooks), each with its Checks, in the order it runs them.
GIT_HOOKS: Dict[str, List[str]] = {}
for _c in _GIT_HOOK_CHECKS:
    GIT_HOOKS.setdefault(_c.hook, []).append(_c.name)
del _c


def run(
    name: str, args: List[str], in_: Input, on: Callable[[str], bool], stderr: TextIO
) -> Optional[int]:
    """Runs the Check `name` a Git hook runs with git's arguments `args`, when `on` says the Config
    turns it on, and returns its exit code for git: 0 when it finds nothing or is off, 1 with what
    it found on `stderr`, 2 with why it couldn't check. None when there is no such Check, or `args`
    aren't the ones it takes."""
    for c in _GIT_HOOK_CHECKS:
        if c.name != name:
            continue
        if (c.arg == "") != (len(args) == 0) or len(args) > 1:
            return None
        if not on(name):
            return 0
        prefix = f"{names.PLUGIN}:{name}: "
        try:
            found = c.find(in_, args[0] if args else "")
        except (Error, OSError) as e:
            stderr.write(f"{prefix}{e}\n")
            return 2
        if not found:
            return 0
        if c.advice:
            prefix += c.advice + ":\n"
        stderr.write(prefix + "\n".join(found) + "\n")
        return 1
    return None


def run_hook(
    hook: str, args: List[str], in_: Input, on: Callable[[str], bool], stderr: TextIO
) -> Optional[int]:
    """Runs the Checks of the Git hook `hook` (ADR git-hooks) that `on` turns on, all of them, each
    with the first of git's arguments `args` if it takes one, and returns the worst of their exit
    codes. None when the plugin writes no such Git hook, or git gives none of the arguments one of
    its Checks takes."""
    if hook not in GIT_HOOKS:
        return None
    own = []
    for c in _GIT_HOOK_CHECKS:
        if c.hook != hook:
            continue
        if c.arg == "":
            own.append([])
        elif not args:
            return None
        else:
            own.append(args[:1])
    code = 0
    for i, name in enumerate(GIT_HOOKS[hook]):
        c = run(name, own[i], in_, on, stderr)
        if c is None:  # the registry and run disagree: fail rather than skip the Check
            stderr.write(f"{names.PLUGIN}:{name}: could not run it\n")
            c = 2
        code = max(code, c)
    return code


def usage() -> List[str]:
    """How to run each Check a Git hook runs by hand, one line each: `check <name>` with the
    argument it takes or what it reads on stdin."""
    lines = []
    for c in _GIT_HOOK_CHECKS:
        line = "check " + c.name
        if c.arg:
            line += " " + c.arg
        if c.stdin:
            line += " < " + c.stdin
        lines.append(line)
    return lines
