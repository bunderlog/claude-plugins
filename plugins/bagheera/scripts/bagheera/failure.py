"""The last Check that failed, kept in the plugin's data folder for doctor to show (ADR checks): a
Check that raises lets the tool call through, and its Hook's stderr is dropped (ADR binary), so
this is the only trace it leaves. It keeps no word of the call or of the error's message, which
may carry the Secret the call names: only where in the plugin's code it failed."""

from __future__ import annotations

import json
import os
import time
import traceback
from typing import Optional

from bagheera import names, version

FILE = "check-failure.json"

# The folder the plugin's package is in, so a failure's place is named within it.
_SCRIPTS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def record(data: str, check: str, tool: str, error: BaseException) -> None:
    """Keeps in the data folder `data` that the Check `check` raised `error` on a call of the tool
    `tool`, in place of the failure kept before; nothing where it can't."""
    if not data:
        return
    at = ""
    for frame in traceback.extract_tb(error.__traceback__):
        path = os.path.realpath(frame.filename)
        if path.startswith(_SCRIPTS + os.sep):
            at = f"{os.path.relpath(path, _SCRIPTS)}:{frame.lineno}"
    kept = {
        "version": version.read(), "time": int(time.time()), "check": check, "tool": tool,
        "error": type(error).__name__, "at": at,
    }
    try:
        os.makedirs(data, mode=0o700, exist_ok=True)
        with open(os.path.join(data, FILE), "w", encoding="utf-8") as f:
            json.dump(kept, f)
    except OSError:
        pass


def problem(data: str) -> Optional[str]:
    """doctor's problem of the Check that failed last, while the version that failed runs; None
    where none failed in it, and where the file can't be read."""
    try:
        with open(os.path.join(data, FILE), encoding="utf-8") as f:
            kept = json.load(f)
        if kept.get("version") != version.read():
            return None
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(kept["time"])))
        where = f" at {kept['at']}" if kept.get("at") else ""
        return (
            f"{names.PLUGIN}:{kept['check']} failed on a {kept['tool']} call at {when} "
            f"({kept['error']}{where}) and let it through: report it at "
            f"https://github.com/{names.MARKETPLACE_REPO}/issues; the Release that fixes it "
            "stops showing this"
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
