"""Writes the Git hooks that run the Checks the Config turns on, and the commands it sets, at
session start (ADR git-hooks): into the folder git runs them from, or with husky 9 into the git
folder, with a line in husky's own Git hook that runs each."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from baloo import binlink, checks, names, settings


@dataclass
class Blocked:
    """A Git hook of someone else's, at `path`, and what it keeps from running: Checks, and the
    command the Config sets for it."""

    path: str
    runs: List[str]


@dataclass
class Report:
    """What write did and what it left alone."""

    # The folder the plugin's Git hooks are in.
    dir: str = ""
    # The Git hooks it wrote where none of the plugin's was, and took out.
    written: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    # The files of husky's it changed, from the repo's root, for the user to commit.
    husky: List[str] = field(default_factory=list)
    # The Git hooks it didn't write and left alone, which keep Checks that are on, or a command,
    # from running.
    theirs: List[Blocked] = field(default_factory=list)


def write(root: str, data: str, on: Callable[[str], bool]) -> Tuple[Report, Optional[Exception]]:
    """Brings the Git hooks of the repo at `root` in line with `on`, which says whether a Check is
    on, or a Git hook's command is set (see _runs): it writes each Git hook that runs either,
    running the plugin through the link in `data`, the plugin's data folder (see binlink), and
    takes out its own that runs neither. It returns what it did, with what went wrong, or None;
    what it did before that went wrong is in the Report too."""
    try:
        dir, husky = _locate(root)
    except (OSError, checks.Error) as e:
        return Report(), e
    if dir == os.devnull:  # git runs no Git hooks, as in a run of `claude plugin eval`
        return Report(), None
    r = Report(dir=dir)
    try:
        _write(r, root, data, on, husky)
    except (OSError, ValueError) as e:
        return r, e
    return r, None


def _write(r: Report, root: str, data: str, on: Callable[[str], bool], husky: bool) -> None:
    in_tree = not husky and _inside(root, r.dir)
    link = ""
    for hook in sorted(checks.GIT_HOOKS):
        running = _runs(hook, on)
        path = os.path.join(r.dir, hook)
        current = _read(path)
        had = current is not None
        if had and not _ours(current):
            if running:
                r.theirs.append(Blocked(path, running))
            continue
        if not running:
            if had:
                os.remove(path)
                r.removed.append(hook)
        else:
            if not link:
                link = binlink.point(data)
            want = _script(link, hook)
            if current != want:
                _replace(path, want, 0o755)
                if not had:
                    r.written.append(hook)
            if in_tree:
                settings.exclude(root, path)
        if husky:
            if _husky_runs(os.path.join(root, ".husky", hook), hook, bool(running)):
                r.husky.append(".husky/" + hook)


def _locate(root: str) -> Tuple[str, bool]:
    """The folder the plugin's Git hooks of the repo at `root` go in, and whether husky 9 runs the
    repo's Git hooks, so the plugin's are in the git folder's instead (ADR git-hooks)."""
    p = subprocess.run(
        ["git", "-C", root, "rev-parse", "--git-path", "hooks", "--git-common-dir"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    if p.returncode != 0:
        raise checks.Error(f"git rev-parse: exit status {p.returncode}")
    out = p.stdout
    paths = out[:-1].split("\n") if out.endswith("\n") else out.split("\n")
    if len(paths) != 2:
        raise checks.Error(f"git rev-parse printed {out!r}")
    hooks, common = [p if os.path.isabs(p) else os.path.join(root, p) for p in paths]
    hooks, common = os.path.normpath(hooks), os.path.normpath(common)
    if hooks == os.path.join(root, ".husky", "_") and os.path.exists(os.path.join(hooks, "h")):
        return os.path.join(common, names.PLUGIN + "-hooks"), True
    return hooks, False


def _runs(hook: str, on: Callable[[str], bool]) -> List[str]:
    """What the Git hook `hook` runs, in order: its Checks that `on` turns on, then its command,
    named `git-hook-commands.<hook>`, where `on` says the Config sets one."""
    return [n for n in checks.GIT_HOOKS[hook] + [names.GIT_HOOK_COMMANDS + "." + hook] if on(n)]


# What inspect finds of one of the plugin's Git hooks.
# It runs nothing (see _runs), and no Git hook of the plugin's is there.
OFF = "off"
# The plugin's, as session start writes it, runs what it runs.
RUNNING = "running"
# It runs something, but no Git hook is there.
MISSING = "missing"
# A Git hook the plugin didn't write is there, and keeps what it runs from running.
THEIRS = "theirs"
# The plugin's is there, but not as session start would write it now, such as one running the
# link in another data folder, or one the Go binary wrote.
OUTDATED = "outdated"
# The plugin's is there, but it runs nothing.
LEFTOVER = "leftover"


@dataclass
class Hook:
    """One of the plugin's Git hooks as inspect finds it."""

    name: str
    path: str
    # What it runs: its Checks the Config turns on, then its command (see _runs).
    runs: List[str]
    state: str = OFF
    # The link the plugin's Git hook runs the plugin through, read from it; "" where none of the
    # plugin's is there.
    link: str = ""
    # With husky 9, that husky's own Git hook isn't as session start keeps it: running the
    # plugin's where Checks are on, and not where none is.
    husky_outdated: bool = False


def inspect(root: str, data: str, on: Callable[[str], bool]) -> Tuple[str, bool, List[Hook]]:
    """The Git hooks of the repo at `root` as they are, against what write would make of them with
    `on` and the link in `data`, the plugin's data folder; it changes nothing. It returns the
    folder they are in, whether husky 9 runs them, and each one; it raises OSError or
    checks.Error where it can't read them."""
    dir, husky = _locate(root)
    link = os.path.join(data, names.PLUGIN)
    hooks: List[Hook] = []
    for name in sorted(checks.GIT_HOOKS):
        h = Hook(name, os.path.join(dir, name), _runs(name, on))
        text = _read(h.path)
        had = text is not None
        if text is not None and not _ours(text):
            h.state = THEIRS if h.runs else OFF
        elif not had:
            h.state = MISSING if h.runs else OFF
        elif not h.runs:
            h.state = LEFTOVER
        elif data and text == _script(link, name):
            h.state = RUNNING
        else:
            h.state = OUTDATED
        if text is not None and _ours(text):
            h.link = _runs_link(text)
        if husky:
            try:
                theirs = _read(os.path.join(root, ".husky", name)) or ""
            except OSError:
                theirs = ""
            has = _husky_line(name) in theirs.split("\n")
            h.husky_outdated = has != bool(h.runs)
        hooks.append(h)
    return dir, husky, hooks


def _runs_link(text: str) -> str:
    """The link the plugin's Git hook `text` runs the plugin through, as _script writes it, or
    ""; for one the Go binary wrote, the binary's link."""
    for line in text.split("\n"):
        if line.startswith("b="):
            return line[2:].strip("'").replace("'\\''", "'")
    return ""


def _script(link: str, hook: str) -> str:
    """The Git hook `hook` that runs the plugin through the link `link`, marked as the plugin's on
    its second line. Where the link or python3 is missing, it says why the Checks didn't run, and
    passes (ADR git-hooks, ADR binary)."""
    plugin = names.PLUGIN
    return (
        "#!/bin/sh\n"
        f"{names.MARKER}: runs the plugin's Checks, rewritten at each session start\n"
        f"b={_quote(link)}\n"
        f'[ -f "$b/scripts/run.py" ] || '
        f"{{ echo \"{plugin}: $b is missing, so the plugin's Checks didn't run\" >&2; exit 0; }}\n"
        "command -v python3 >/dev/null 2>&1 || "
        f"{{ echo \"{plugin}: python3 is missing, so the plugin's Checks didn't run\" >&2; exit 0; }}\n"
        f'exec python3 -E -s "$b/scripts/run.py" git-hook {hook} "$@"\n'
    )


def _ours(text: str) -> bool:
    """Whether the Git hook `text` is one the plugin wrote."""
    _, _, rest = text.partition("\n")
    return rest.startswith(names.MARKER)


def _husky_line(hook: str) -> str:
    """The line in husky's Git hook `hook` that runs the plugin's, if it is there: the same in
    every clone, for it is committed."""
    return (
        f'baloo_hook="$(git rev-parse --git-common-dir)/{names.PLUGIN}-hooks/{hook}"; '
        f'[ ! -x "$baloo_hook" ] || "$baloo_hook" "$@" || exit $? {names.MARKER}'
    )


def _husky_runs(path: str, hook: str, run: bool) -> bool:
    """Puts the line that runs the plugin's Git hook `hook` first in husky's at `path`, after its
    #! line if it has one, creating the file when missing; or, not `run`, takes the line out, and
    the file with it when the line was all of it. It says whether it changed the file."""
    data = _read(path) or ""
    parts = data.split("\n")
    lines = [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])
    kept = [line for line in lines if not line.rstrip("\n").endswith(names.MARKER)]
    if run:
        at = 1 if kept and kept[0].startswith("#!") else 0
        kept.insert(at, _husky_line(hook) + "\n")
    text = "".join(kept)
    if text == data:
        return False
    if not text.strip():
        os.remove(path)
        return True
    try:
        mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        mode = 0o644
    _replace(path, text, mode)
    return True


def _read(path: str) -> Optional[str]:
    """The file at `path`, or None where it isn't there."""
    try:
        with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _replace(path: str, text: str, mode: int) -> None:
    """Writes `text` to the file at `path` with the mode `mode` in one step, so git never runs
    half a Git hook."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _quote(s: str) -> str:
    """`s` quoted for sh."""
    return "'" + s.replace("'", "'\\''") + "'"


def _inside(dir: str, path: str) -> bool:
    """Whether `path` is in the folder `dir`."""
    rel = os.path.relpath(path, dir)
    return rel != ".." and not rel.startswith(".." + os.sep)
