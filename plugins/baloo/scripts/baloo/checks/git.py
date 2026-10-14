"""Runs git for the Checks, and says why it failed."""

from __future__ import annotations

import subprocess
from typing import Optional


class Error(Exception):
    """Why a Check couldn't check, such as git failing outside a repo."""


def git(dir: str, *args: str, stdin: Optional[str] = None, env: Optional[dict] = None) -> str:
    """What git, run in `dir` with `args`, prints; an Error with why it failed."""
    p = subprocess.run(
        ["git", "-C", dir, *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if p.returncode != 0:
        raise Error(f"git {args[0]}: exit status {p.returncode}: {p.stderr.strip()}")
    return p.stdout
