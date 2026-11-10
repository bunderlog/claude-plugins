"""What a session was told once, marked in the plugin's data folder and forgotten after a week."""

from __future__ import annotations

import os
import time

# How long a mark is kept: a week.
KEPT = 7 * 24 * 3600


def first(data: str, kind: str, session: str) -> bool:
    """Whether the session `session` hasn't been told of `kind` yet, marking it told in the
    plugin's data folder `data`; False without the folder or the session, or where the mark can't
    be written, so nothing is told on every prompt."""
    if not data or not session:
        return False
    folder = os.path.join(data, kind, "shown")
    path = os.path.join(folder, session)
    try:
        now = time.time()
        for e in os.scandir(folder) if os.path.isdir(folder) else []:
            if now - e.stat().st_mtime > KEPT:
                os.remove(e.path)
        if os.path.exists(path):
            return False
        os.makedirs(folder, mode=0o700, exist_ok=True)
        with open(path, "w"):
            pass
    except OSError:
        return False
    return True
