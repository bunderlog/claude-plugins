"""Picks one of the plugin's Output styles for a project, in the Claude Code settings file of the
project that enables the plugin, where none of Claude Code's settings files picks one already (ADR
output-styles)."""

from __future__ import annotations

from typing import NamedTuple, Optional, Tuple

from baloo import names, settings


class Picked(NamedTuple):
    """An Output style pick wrote: the file, and the Scope whose settings enable the plugin."""

    path: str
    enabled: str


def pick(project: str, root: str, style: str) -> Tuple[Picked, Optional[Exception]]:
    """Sets outputStyle to the plugin's `style` for the project at `project`, in the repo at `root`,
    where the plugin is enabled in its local, project or user settings, and none of Claude Code's
    settings files sets outputStyle already, to any value. It writes the file that enables the
    plugin: the project's settings.json or settings.local.json, or for the user's settings the
    project's settings.local.json. It returns what it wrote, a Picked of "" when it wrote nothing,
    with what went wrong, or None. A file it creates goes into the repo's info/exclude, as Claude
    Code does with its own."""
    path, enabled, err = settings.set_unset(
        project, root, ["outputStyle"], "outputStyle", names.PLUGIN + ":" + style
    )
    return Picked(path, enabled), err
