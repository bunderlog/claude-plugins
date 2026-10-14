"""Reads Claude Code's settings files for a project and writes one of their top-level fields, the
rest of the file's text as it was, for what session start sets in them (ADR output-styles, ADR
status-line)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from baloo import names

# The Scopes, Claude Code's settings files for a project, by whom each is for.
LOCAL = "local"  # the project's .claude/settings.local.json, one person's
PROJECT = "project"  # the project's .claude/settings.json, its team's
USER = "user"  # the user's own settings.json, for every project
MANAGED = "managed"  # the machine's managed settings

# The Scopes from the most specific to the least, managed last, since it wins over all of them.
SCOPES = [LOCAL, PROJECT, USER, MANAGED]


def managed() -> str:
    """Claude Code's managed settings file on this machine; a test points it elsewhere with
    BALOO_MANAGED_SETTINGS."""
    path = os.environ.get("BALOO_MANAGED_SETTINGS", "")
    if path:
        return path
    return {
        "darwin": "/Library/Application Support/ClaudeCode/managed-settings.json",
        "linux": "/etc/claude-code/managed-settings.json",
    }.get(sys.platform, "")


def own() -> str:
    """Claude Code's own folder, $CLAUDE_CONFIG_DIR or ~/.claude, or "" where neither is known."""
    folder = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if folder:
        return folder
    home = os.environ.get("HOME", "")
    return os.path.join(home, ".claude") if home else ""


def files(project: str) -> Dict[str, str]:
    """Claude Code's settings files for the project at `project`, by Scope; one Claude Code
    doesn't have is ""."""
    folder = own()
    user = os.path.join(folder, os.path.basename(names.PROJECT_SETTINGS)) if folder else ""
    return {
        LOCAL: os.path.join(project, names.LOCAL_SETTINGS),
        PROJECT: os.path.join(project, names.PROJECT_SETTINGS),
        USER: user,
        MANAGED: managed(),
    }


def read_all(paths: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Every settings file in `paths`, its top-level fields, by Scope."""
    return {scope: _read(paths.get(scope, "")) for scope in SCOPES}


def _read(path: str) -> Dict[str, Any]:
    """The settings file at `path`, its top-level fields; one that isn't there, or is empty, has
    none."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        return {}
    if not data.strip():
        return {}
    try:
        fields = json.loads(data)
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None
    if fields is None:
        return {}
    if not isinstance(fields, dict):
        raise ValueError(f"{path}: not a JSON object")
    return fields


def enabling(fields: Dict[str, Dict[str, Any]]) -> str:
    """The Scope whose settings `fields` enable the plugin, or "" when none does: of the local,
    project and user settings, the most specific whose enabledPlugins names it decides, as in
    Claude Code. Managed settings don't count: a plugin they enable is the machine's, not a
    choice made for the project."""
    for scope in (LOCAL, PROJECT, USER):
        plugins = fields.get(scope, {}).get("enabledPlugins")
        if not isinstance(plugins, dict):
            continue
        if names.PLUGIN_ID in plugins:
            return scope if plugins[names.PLUGIN_ID] is True else ""
    return ""


def set_unset(
    project: str, root: str, keys: List[str], key: str, value: Any
) -> Tuple[str, str, Optional[Exception]]:
    """Sets the top-level field `key` to `value` for the project at `project`, in the repo at
    `root`, where the plugin is enabled in its local, project or user settings and none of Claude
    Code's settings files sets any of `keys`, to any value. It writes the file that enables the
    plugin: the project's settings.json or settings.local.json, or for the user's settings the
    project's settings.local.json. It returns the file it wrote and the Scope that enables the
    plugin, or "" for both where it wrote nothing, with what went wrong, or None. A file it creates
    goes into the repo's info/exclude, as Claude Code does with its own; since the file is written
    even when that fails, the error is returned beside its path rather than raised."""
    paths = files(project)
    try:
        fields = read_all(paths)
    except (OSError, ValueError) as e:
        return "", "", e
    for f in fields.values():
        if any(k in f for k in keys):
            return "", "", None
    enabled = enabling(fields)
    if not enabled:
        return "", "", None
    path = paths[PROJECT] if enabled == PROJECT else paths[LOCAL]
    try:
        created = set_field(path, key, value)
    except (OSError, ValueError) as e:
        return "", "", e
    if created:
        try:
            exclude(root, path)
        except (OSError, ValueError) as e:
            return path, enabled, e
    return path, enabled, None


def set_field(path: str, key: str, value: Any) -> bool:
    """Sets the top-level field `key` of the settings file at `path` to `value`, the rest of the
    file's text as it was, and says whether it created the file, which then goes into the repo's
    info/exclude (see exclude)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
        created = False
    except FileNotFoundError:
        data, created = "", True
    try:
        out = _set(data, key, json.dumps(value, separators=(",", ":"), ensure_ascii=False))
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None
    _replace(path, out)
    return created


def delete(path: str, key: str) -> None:
    """Takes the top-level field `key` out of the settings file at `path`, the rest of the file's
    text as it was; a file without it is left alone."""
    with open(path, encoding="utf-8") as f:
        data = f.read()
    found = _find(data, key)
    if found is None:
        return
    member, _ = found
    out = data[: member[0]] + data[member[1] :]
    if not _valid(out):
        raise ValueError(f"{path}: could not take out {key}")
    _replace(path, out)


def _set(data: str, key: str, value: str) -> str:
    """The settings file `data` with its top-level field `key` set to the JSON `value`: in place
    where it has the field, else first in it, the rest of the file as it was; no data, or an
    object with nothing in it, is a new file."""
    field = json.dumps(key) + ": " + value
    fields = json.loads(data) if data.strip() else None
    if fields is not None and not isinstance(fields, dict):
        raise ValueError("not a JSON object")
    if not fields:
        return "{\n  " + field + "\n}\n"
    found = _find(data, key)
    if found is not None:
        _, old = found
        out = data[: old[0]] + value + data[old[1] :]
    else:
        i = data.index("{")
        out = data[: i + 1] + "\n  " + field + "," + data[i + 1 :]
    if not _valid(out):
        raise ValueError("could not set " + key)
    return out


_WS = " \t\r\n"
_decoder = json.JSONDecoder()


def _skip(data: str, i: int) -> int:
    while i < len(data) and data[i] in _WS:
        i += 1
    return i


def _find(data: str, key: str) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Where the top-level field `key` is in the JSON object `data`, as offsets: the field whole,
    with the comma that parts it from the one before, or for the first field from the one after,
    and its value alone; None when the object has no such field."""
    i = _skip(data, 0)
    if data[i : i + 1] != "{":
        raise ValueError("not a JSON object")
    i += 1
    first = True
    while True:
        start = _skip(data, i)
        if data[start : start + 1] == "}":
            return None
        j = start
        if not first:
            if data[j : j + 1] != ",":
                raise ValueError(f"expected , at offset {j}")
            j = _skip(data, j + 1)
        name, j = _decoder.raw_decode(data, j)
        if not isinstance(name, str):
            raise ValueError(f"expected a field's name at offset {start}")
        j = _skip(data, j)
        if data[j : j + 1] != ":":
            raise ValueError(f"expected : at offset {j}")
        begin = _skip(data, j + 1)
        _, end = _decoder.raw_decode(data, begin)
        if name == key:
            member = [start, end]
            if first:
                # The first field goes with the comma after it and the space up to the next one,
                # and the only one with the space before it.
                after = _skip(data, end)
                if data[after : after + 1] == ",":
                    member[1] = _skip(data, after + 1)
                else:
                    member[0] = data.index("{") + 1
            return (member[0], member[1]), (begin, end)
        i = end
        first = False


def _valid(data: str) -> bool:
    try:
        json.loads(data)
    except ValueError:
        return False
    return True


def _replace(path: str, data: str) -> None:
    """Writes `data` to the file at `path` whole or not at all: to a new file beside it, then
    renamed over it, so a write cut short, or one of Claude Code's own at the same moment, never
    leaves half a settings file. A link is followed, and the file keeps its mode."""
    if os.path.exists(path):
        path = os.path.realpath(path)
    try:
        mode = os.stat(path).st_mode & 0o777
    except OSError:
        mode = 0o644
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def exclude(root: str, path: str) -> None:
    """Adds the file at `path` to the info/exclude of the repo at `root`, unless it is there, as
    Claude Code does with a settings.local.json it creates."""
    rel = os.path.relpath(path, root)
    line = "/" + _pattern(rel.replace(os.sep, "/"))
    file = os.path.join(_git_dir(root), "info", "exclude")
    try:
        with open(file, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        data = ""
    if any(kept.strip() == line for kept in data.split("\n")):
        return
    if data and not data.endswith("\n"):
        line = "\n" + line
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _pattern(rel: str) -> str:
    """The gitignore pattern that matches the path `rel` and nothing else: its wildcards and
    backslashes escaped, and a trailing space kept."""
    p = "".join("\\" + c if c in "\\*?[" else c for c in rel)
    trimmed = p.rstrip(" ")
    return trimmed + "\\ " * (len(p) - len(trimmed))


def _git_dir(root: str) -> str:
    """The folder holding the info/ of the repo at `root`: its .git folder, or for a worktree,
    whose .git is a file naming its own folder, the folder its worktrees share."""
    folder = os.path.join(root, ".git")
    if os.path.isdir(folder):
        return folder
    with open(folder, encoding="utf-8") as f:
        text = f.read().strip()
    if not text.startswith("gitdir: "):
        raise ValueError(f"{folder} names no gitdir")
    named = os.path.normpath(os.path.join(root, text[len("gitdir: ") :]))
    try:
        with open(os.path.join(named, "commondir"), encoding="utf-8") as f:
            shared = f.read().strip()
    except FileNotFoundError:
        return named
    return os.path.normpath(os.path.join(named, shared))
