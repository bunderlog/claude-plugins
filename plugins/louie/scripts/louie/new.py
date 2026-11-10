"""The `new` command that /louie:new runs: it writes the go-vue template into a new or empty folder
outside any git repo, filling in the product's name, its owner and today's date, runs `git init`
on main, and prints the one line the person runs to turn the Git hooks on and make the first
commit (PRD templates)."""

from __future__ import annotations

import datetime
import os
import re
import shlex
import shutil
import subprocess
from typing import Dict, List, Optional, TextIO

from louie import binlink, names, version

# A product's name, usable as a Go, npm and Kamal name.
NAME = re.compile(r"[a-z][a-z0-9-]*")
# The owner's name on GitHub, which stands in the Go module's path: letters, digits and single
# hyphens, not at either end, and at most 39 of them.
OWNER = re.compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9])*")
_OWNER_MAX = 39
# The template's folder in the plugin.
TEMPLATE = os.path.join(binlink.PLUGIN, names.TEMPLATES, names.TEMPLATE)
# The template's folder whose files git runs, which are written executable whatever mode the
# plugin's copy has.
_EXECUTABLE = ".githooks"
# What would point git at another repo than the folder it is run in, as in a Git hook.
_LOCATING = [
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
    "GIT_PREFIX", "GIT_CEILING_DIRECTORIES",
]


def run(path: str, name: str, owner: str, stdout: TextIO, stderr: TextIO) -> int:
    """Writes the template to `path` for the product `name` of `owner`: exit 0, with the line to
    run last on stdout; or exit 1 with why on stderr, and nothing written."""
    target = os.path.abspath(os.path.expanduser(path)) if path else ""
    why = _refusal(target, name, owner)
    if why:
        stderr.write(f"{names.PLUGIN}: {why}, so nothing was written\n")
        return 1
    top = _topmost_missing(target)
    marks = {
        "__NAME__": name,
        "__OWNER__": owner,
        "__DATE__": datetime.date.today().isoformat(),
    }
    try:
        os.makedirs(target, exist_ok=True)
        _write(target, marks)
        _git(target, "init", "-q", "--initial-branch=main")
    except OSError as e:
        _undo(target, top)
        stderr.write(f"{names.PLUGIN}: {e}, so what was written is removed\n")
        return 1
    v = version.read()
    stdout.write(
        f"{names.PLUGIN}: wrote the {names.TEMPLATE} template {v} to {target} and ran git init "
        "on main; to turn its Git hooks on and make the first commit, run:\n"
        f"! cd {shlex.quote(target)} && mise trust && mise run setup && git add -A && "
        f'git commit -m "chore: scaffold from {names.PLUGIN} {names.TEMPLATE} {v}"\n'
    )
    return 0


def _refusal(target: str, name: str, owner: str) -> str:
    """Why the template can't be written to `target`, or "" where it can."""
    if not NAME.fullmatch(name):
        return (
            f"the name {name!r} isn't lowercase letters, digits and hyphens starting with a letter"
        )
    if not OWNER.fullmatch(owner) or len(owner) > _OWNER_MAX:
        return (
            f"the owner {owner!r} isn't at most {_OWNER_MAX} letters, digits and single hyphens, "
            "not starting or ending with one"
        )
    if not target:
        return "no folder is given"
    if shutil.which("git") is None:
        return "git isn't on PATH"
    if os.path.lexists(target):
        if not os.path.isdir(target):
            return f"{target} isn't a folder"
        if os.listdir(target):
            return f"{target} holds files"
    existing = target
    while not os.path.lexists(existing):
        existing = os.path.dirname(existing)
    if not os.path.isdir(existing):
        return f"{existing} isn't a folder"
    try:
        p = _run_git(existing, "rev-parse", "--is-inside-work-tree")
    except OSError as e:
        return f"git can't run: {e}"
    if p.returncode == 0:
        return f"{target} is inside a git repo"
    return ""


def _topmost_missing(target: str) -> Optional[str]:
    """The topmost folder of `target`'s path that doesn't exist yet, `target` itself among them;
    None where `target` exists."""
    top = None
    d = target
    while not os.path.lexists(d):
        top = d
        d = os.path.dirname(d)
    return top


def _write(target: str, marks: Dict[str, str]) -> None:
    """Writes each file of the template to `target`, its name without the template's suffix and
    its text with `marks` filled in."""
    for folder, dirs, files in os.walk(TEMPLATE):
        dirs.sort()
        rel_folder = os.path.relpath(folder, TEMPLATE)
        for file in sorted(files):
            rel = os.path.normpath(os.path.join(rel_folder, file))
            if rel.endswith(names.TEMPLATE_SUFFIX):
                rel = rel[: -len(names.TEMPLATE_SUFFIX)]
            with open(os.path.join(folder, file), encoding="utf-8", newline="") as f:
                text = f.read()
            for mark, value in marks.items():
                text = text.replace(mark, value)
            dest = os.path.join(target, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            first = rel.split(os.sep)[0]
            os.chmod(dest, 0o755 if first == _EXECUTABLE else 0o644)


def _undo(target: str, top: Optional[str]) -> None:
    """Removes what writing to `target` made: the folders that didn't exist, from `top`, or else
    what is in `target`, which was empty."""
    if top is not None:
        shutil.rmtree(top, ignore_errors=True)
        return
    try:
        entries: List[str] = os.listdir(target)
    except OSError:
        return
    for entry in entries:
        path = os.path.join(target, entry)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.remove(path)
            except OSError:
                pass


def _run_git(dir: str, *args: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _LOCATING}
    return subprocess.run(
        ["git", "-C", dir, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=env, timeout=60,
    )


def _git(dir: str, *args: str) -> None:
    """Runs git in `dir` with `args`; an OSError where it fails."""
    try:
        p = _run_git(dir, *args)
    except subprocess.TimeoutExpired as e:
        raise OSError(f"git {' '.join(args)}: {e}") from e
    if p.returncode != 0:
        raise OSError(f"git {' '.join(args)}: {p.stderr.strip() or f'exit {p.returncode}'}")
