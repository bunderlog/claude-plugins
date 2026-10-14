"""The plugin's version: its manifest's, since the code ships inside the plugin with nothing built
(ADR binary)."""

from __future__ import annotations

import json
import os

from baloo import binlink


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
