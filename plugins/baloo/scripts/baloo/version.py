"""The plugin's version: its manifest's, since the code ships inside the plugin with nothing built
(ADR binary), and the one Claude Code records as installed, which a session started before an
update doesn't run (ADR doctor)."""

from __future__ import annotations

import json
import os

from baloo import binlink, names, settings


def read() -> str:
    """The version in the manifest of the plugin this code is in, or "dev" where it has none."""
    path = os.path.join(binlink.PLUGIN, ".claude-plugin", "plugin.json")
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        return "dev"
    v = manifest.get("version") if isinstance(manifest, dict) else None
    return v if isinstance(v, str) and v else "dev"


def installed(root: str) -> str:
    """The version Claude Code records as installed for the repo at `root`, in its own folder's
    plugins/installed_plugins.json: the project's or local install, else the user's; "" where it
    records none, or the file has another shape, as it is Claude Code's and undocumented."""
    own = settings.own()
    try:
        with open(os.path.join(own, "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            data = json.load(f)
        entries = data["plugins"][names.PLUGIN_ID]
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    if not own or not isinstance(entries, list):
        return ""
    here = os.path.realpath(root)
    found = {"": ""}
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("version"), str):
            continue
        project = e.get("projectPath")
        if e.get("scope") == "user":
            found.setdefault("user", e["version"])
        elif isinstance(project, str) and os.path.realpath(project) == here:
            found.setdefault("project", e["version"])
    return found.get("project") or found.get("user") or ""


def _numbers(v: str):
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return None


def newer_installed(root: str) -> str:
    """The version installed for the repo at `root` where it is newer than the one running, which
    only a restart of Claude Code runs; "" otherwise, a running copy that isn't a Release too."""
    there = installed(root)
    running, newer = _numbers(read()), _numbers(there)
    return there if running and newer and newer > running else ""
