"""The Check no-git-hook-bypass."""

from __future__ import annotations

import os
import re
from typing import List

from bagheera.checks.shell import has_flag, programs, split_git


def no_git_hook_bypass(command: str, cwd: str = "") -> str:
    """The Check no-git-hook-bypass (PreToolUse on Bash): why the shell command `command`, run in
    the folder `cwd`, would bypass the Git hooks, or "" when it wouldn't. That is `--no-verify` on
    any git subcommand, or an abbreviation of it git takes, `-n` on commit, core.hooksPath set for
    one command, through git's options or its GIT_CONFIG_* variables, or written to git's config
    but where it turns the repo's own Git hooks on (ADR checks), and HUSKY=0, which turns off
    husky and the Git hooks it runs."""
    progs = programs(command)
    # After a cd the folder git runs in is unknown, so no write of core.hooksPath goes through.
    moves = any(p.name in ("cd", "pushd") for p in progs)
    for p in progs:
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
            if not moves and _turns_hooks_on(options, rest, cwd):
                continue
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
        redirect = _REDIRECT.fullmatch(a)
        if value:
            value = False
        elif redirect:
            # Its target, where it is the next word, is no value either.
            value = not redirect[1]
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


# The folders a set-up project keeps its Git hooks in, as core.hooksPath names them (PRD
# project-setup): `.githooks`, or husky's `.husky/_`.
_HOOK_FOLDERS = [".githooks", os.path.join(".husky", "_")]


def _turns_hooks_on(options: List[str], args: List[str], cwd: str) -> bool:
    """Whether `git <options> config <args>`, run in `cwd`, sets core.hooksPath in the clone's own
    config to a folder of _HOOK_FOLDERS that is in the repo, which turns its Git hooks on. Any
    other scope, value or git option is no such write: a path without hooks turns them off."""
    folder = cwd
    for i in range(0, len(options), 2):
        if options[i] != "-C" or i + 1 >= len(options) or not folder:
            return False
        folder = os.path.join(folder, options[i + 1])
    words: List[str] = []
    target = False
    for a in args:
        redirect = _REDIRECT.fullmatch(a)
        if target:
            target = False
        elif redirect:
            target = not redirect[1]
        elif a != "--local":
            words.append(a)
    if words[:1] == ["set"]:
        words = words[1:]
    if len(words) != 2 or not _hooks_path(words[0]) or words[1].startswith("-"):
        return False
    value = os.path.normpath(words[1])
    root = _repo_root(folder)
    return value in _HOOK_FOLDERS and bool(root) and os.path.isdir(os.path.join(root, value))


def _repo_root(folder: str) -> str:
    """The root of the git repo `folder` is in, where core.hooksPath's relative path starts, or ""
    outside one."""
    if not folder:
        return ""
    here = os.path.abspath(folder)
    while True:
        if os.path.exists(os.path.join(here, ".git")):
            return here
        up = os.path.dirname(here)
        if up == here:
            return ""
        here = up


# A redirection, `2>/dev/null` or the `2>` the split leaves of `2>&1`, with its target.
_REDIRECT = re.compile(r"\d*(?:>>?|<|&>>?)(.*)", re.S)

# git config's options that take the next argument as their value, which is no key.
_CONFIG_VALUED = ["-f", "--file", "--blob", "--type", "--default", "--comment", "--value"]
