"""The Check no-git-hook-bypass."""

from __future__ import annotations

import re
from typing import List

from bagheera.checks.shell import has_flag, programs, split_git


def no_git_hook_bypass(command: str) -> str:
    """The Check no-git-hook-bypass (PreToolUse on Bash): why the shell command `command` would
    bypass the Git hooks, or "" when it wouldn't. That is `--no-verify` on any git subcommand, or
    an abbreviation of it git takes, `-n` on commit, core.hooksPath set for one command, through
    git's options or its GIT_CONFIG_* variables, or written to git's config, and HUSKY=0, which
    turns off husky and the Git hooks it runs."""
    for p in programs(command):
        assigned = p.env + (p.args if p.name == "export" else [])
        if "HUSKY=0" in assigned:
            return "HUSKY=0 turns the Git hooks off"
        if any(_ENV_HOOKS_PATH.match(a) for a in assigned):
            return "GIT_CONFIG_* setting core.hooksPath bypasses the Git hooks"
        if p.name != "git":
            continue
        options, sub, rest = split_git(p.args)
        for i, option in enumerate(options):
            env = option.startswith("--config-env=")
            if (env and _hooks_path(option[len("--config-env=") :])) or (
                option == "-c" and i + 1 < len(options) and _hooks_path(options[i + 1])
            ):
                return "git -c core.hooksPath=… bypasses the Git hooks"
        if any(_no_verify(a) for a in rest) or (sub == "commit" and has_flag(rest, "-n")):
            return f"git {sub} --no-verify bypasses the Git hooks"
        if sub == "config" and _writes_hooks_path(rest):
            return "git config core.hooksPath changes where the Git hooks are"
    return ""


# A variable that sets core.hooksPath for every git it runs: a key of GIT_CONFIG_COUNT's, or
# GIT_CONFIG_PARAMETERS, which `git -c` passes on.
_ENV_HOOKS_PATH = re.compile(
    r"GIT_CONFIG_(KEY_\d+=\s*core\.hookspath\s*\Z|PARAMETERS=.*core\.hookspath)", re.I | re.S
)


def _no_verify(arg: str) -> bool:
    """Whether `arg` is --no-verify, or the shortest abbreviation of it git takes, --no-veri, or a
    longer one: --no-ver could be --no-verbose too."""
    return len(arg) >= len("--no-veri") and "--no-verify".startswith(arg)


def _hooks_path(setting: str) -> bool:
    """Whether `setting`, `key=value` or a key alone, is core.hooksPath."""
    return setting.partition("=")[0].lower() == "core.hookspath"


def _writes_hooks_path(args: List[str]) -> bool:
    """Whether `git config` with the arguments `args` writes or removes core.hooksPath, rather than
    reads it."""
    words: List[str] = []
    writes = False
    value = False
    for a in args:
        if value:
            value = False
        elif a in ("--unset", "--unset-all", "--add", "--replace-all"):
            writes = True
        elif a in _CONFIG_VALUED:
            value = True
        elif not a.startswith("-"):
            words.append(a)
    if words and words[0] in ("set", "unset"):
        words, writes = words[1:], True
    if not words or not _hooks_path(words[0]):
        return False
    return writes or len(words) > 1


# git config's options that take the next argument as their value, which is no key.
_CONFIG_VALUED = ["-f", "--file", "--blob", "--type", "--default", "--comment", "--value"]
