"""The link in the plugin's data folder to the plugin's folder of the version running, which session
start points at it: what the Status line and the Git hooks run through, so their command stays the
same from one version to the next (ADR binary, ADR status-line, ADR git-hooks)."""

from __future__ import annotations

import os

from baloo import names

# The folder of the plugin this code is in, its version's: plugins/baloo/ in this repo, a folder
# of Claude Code's plugin cache where it is installed.
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def point(data: str) -> str:
    """Points the link in `data`, the plugin's data folder, at the plugin's folder of the version
    running, and returns the link's path. The new link replaces the old in one step, so a command
    run meanwhile finds one or the other."""
    if not data:
        raise OSError("CLAUDE_PLUGIN_DATA is not set")
    path = os.path.join(data, names.PLUGIN)
    try:
        if os.readlink(path) == PLUGIN:
            return path
    except OSError:
        pass
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        os.remove(tmp)
    except OSError:
        pass
    os.symlink(PLUGIN, tmp)
    try:
        os.replace(tmp, path)
    except OSError:
        os.remove(tmp)
        raise
    return path
