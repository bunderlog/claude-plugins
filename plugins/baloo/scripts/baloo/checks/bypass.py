"""The Check no-git-hook-bypass."""

from __future__ import annotations

from typing import List

from baloo.checks.shell import has_flag, programs, split_git


def no_git_hook_bypass(command: str) -> str:
    """The Check baloo:no-git-hook-bypass (PreToolUse on Bash): why the shell command `command`
    would bypass the Git hooks, or "" when it wouldn't. That is `--no-verify` on any git
    subcommand, `-n` on commit, core.hooksPath set for one command or written to git's config, and
    HUSKY=0, which turns off husky and the Git hooks it runs."""
    for p in programs(command):
        if "HUSKY=0" in p.env or (p.name == "export" and "HUSKY=0" in p.args):
            return "HUSKY=0 turns the Git hooks off"
        if p.name != "git":
            continue
        options, sub, rest = split_git(p.args)
        for i, option in enumerate(options):
            env = option.startswith("--config-env=")
            if (env and _hooks_path(option[len("--config-env=") :])) or (
                option == "-c" and i + 1 < len(options) and _hooks_path(options[i + 1])
            ):
                return "git -c core.hooksPath=… bypasses the Git hooks"
        if "--no-verify" in rest or (sub == "commit" and has_flag(rest, "-n")):
            return f"git {sub} --no-verify bypasses the Git hooks"
        if sub == "config" and _writes_hooks_path(rest):
            return "git config core.hooksPath changes where the Git hooks are"
    return ""


def _hooks_path(setting: str) -> bool:
    """Whether `setting`, `key=value` or a key alone, is core.hooksPath."""
    return setting.partition("=")[0].lower() == "core.hookspath"


def _writes_hooks_path(args: List[str]) -> bool:
    """Whether `git config` with the arguments `args` writes or removes core.hooksPath, rather than
    reads it."""
    words: List[str] = []
    writes = False
    for a in args:
        if a in ("--unset", "--unset-all", "--add", "--replace-all"):
            writes = True
        elif not a.startswith("-"):
            words.append(a)
    if words and words[0] in ("set", "unset"):
        words, writes = words[1:], True
    if not words or not _hooks_path(words[0]):
        return False
    return writes or len(words) > 1
