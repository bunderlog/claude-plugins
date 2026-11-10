"""Reads Claude Code's settings files for a project, for what session start and doctor report of
them (ADR output-styles, ADR status-line), and keeps a file the plugin creates in a repo out of
git."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict

from bagheera import names, repo

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


def files(project: str) -> Dict[str, str]:
    """Claude Code's settings files for the project at `project`, by Scope; one Claude Code
    doesn't have is ""."""
    folder = repo.own_folder()
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


def exclude(root: str, path: str) -> None:
    """Adds the file at `path` to the info/exclude of the repo at `root`, unless it is there, as
    Claude Code does with a settings.local.json it creates."""
    rel = os.path.relpath(path, root)
    line = "/" + _pattern(rel.replace(os.sep, "/"))
    file = os.path.join(git_dir(root), "info", "exclude")
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


def git_dir(root: str) -> str:
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
