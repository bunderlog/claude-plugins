"""The plugin's version: its manifest's, since the code ships inside the plugin with nothing built
(ADR binary), and the one Claude Code records as installed, which a session started before an
update doesn't run (ADR doctor)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from bagheera import binlink, names, repo


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


def records() -> Optional[Dict[str, Any]]:
    """What Claude Code records as installed, by plugin, from its own folder's
    plugins/installed_plugins.json; None where the file isn't there or has another shape, as it is
    Claude Code's and undocumented, and nothing can be said of any plugin's version."""
    own = repo.own_folder()
    if not own:
        return None
    try:
        with open(os.path.join(own, "plugins", "installed_plugins.json"), encoding="utf-8") as f:
            data = json.load(f)
        plugins = data["plugins"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return plugins if isinstance(plugins, dict) else None


def installed(root: str, plugin: str = names.PLUGIN_ID) -> str:
    """The version Claude Code records as installed of `plugin` for the repo at `root`: the install
    for this project, whatever its scope, else the user's; "" where it records none."""
    return install(root, plugin)[0]


def install(root: str, plugin: str = names.PLUGIN_ID) -> Tuple[str, str]:
    """The version and the scope (`project`, `local` or `user`) of the install `installed` reads
    for `plugin` and the repo at `root`, which `claude plugin update` is given (PRD setup);
    ("", "") where Claude Code records none."""
    entries = (records() or {}).get(plugin)
    if not isinstance(entries, list):
        return "", ""
    here = os.path.realpath(root)
    found: Dict[str, Tuple[str, str]] = {}
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("version"), str):
            continue
        project, scope = e.get("projectPath"), e.get("scope")
        if scope == "user":
            found.setdefault("user", (e["version"], "user"))
        elif isinstance(project, str) and os.path.realpath(project) == here:
            found.setdefault("project", (e["version"], scope if isinstance(scope, str) and scope
                                         else "project"))
    for where in ("project", "user"):
        if where in found and found[where][0]:
            return found[where]
    return "", ""


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


def older(version: str, than: str) -> bool:
    """Whether `version` is a Release before `than`; False where either isn't a Release."""
    a, b = _numbers(version), _numbers(than)
    return bool(a and b and a < b)
