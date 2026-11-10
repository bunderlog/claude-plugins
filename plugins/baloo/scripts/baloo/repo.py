"""The repo a Hook runs in: the nearest folder up that holds a .git, but not the home folder or
Claude Code's own folder (PRD no-config)."""

from __future__ import annotations

import os

from baloo import settings


def root(folder: str) -> str:
    """The root of the repo `folder` is in, or "" outside a repo, where the repo is the home folder
    itself (a dotfiles repo), or where it is in Claude Code's own folder: the home folder's .claude/
    is Claude Code's own settings, not a repo's, and what is inside it is Claude Code's to write."""
    d = folder
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return "" if _claude_codes(d) else d
        parent = os.path.dirname(d)
        if parent == d:
            return ""
        d = parent


def _claude_codes(root: str) -> bool:
    """Whether the repo root `root` is the home folder, or Claude Code's own folder,
    CLAUDE_CONFIG_DIR or ~/.claude, or inside it, such as a marketplace it cloned."""
    home = os.environ.get("HOME", "")
    if home and os.path.realpath(root) == os.path.realpath(home):
        return True
    own = settings.own()
    if not own:
        return False
    rel = os.path.relpath(os.path.realpath(root), os.path.realpath(own))
    return rel != ".." and not rel.startswith(".." + os.sep)
