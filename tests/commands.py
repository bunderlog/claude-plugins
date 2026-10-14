"""Running the plugin's commands in tests, as its Hooks run them."""

from __future__ import annotations

import io
import json
import os
import unittest
from typing import Tuple
from unittest import mock

from baloo import cli, names
from tests import testkit

# The plugin's folder in this repo.
PLUGIN = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), names.PLUGIN_DIR)
)
# The entry script the Hooks run.
RUN = os.path.join(PLUGIN, "scripts", "run.py")

# What Claude Code or a Session review sets that would change what a command does.
_OUTSIDE = [
    "CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_DATA", "CLAUDE_PLUGIN_ROOT", "CLAUDE_CONFIG_DIR",
    "BALOO_MANAGED_SETTINGS", "BALOO_SESSION_REVIEW", "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SHELL", "COLUMNS",
]


def env(test: unittest.TestCase) -> None:
    """Gives the test `test` an environment of its own, put back when it ends, without what Claude
    Code sets."""
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    test.addCleanup(patcher.stop)
    for key in _OUTSIDE:
        os.environ.pop(key, None)


def chdir(test: unittest.TestCase, dir: str) -> None:
    """Runs the rest of the test `test` in the folder `dir`."""
    old = os.getcwd()
    os.chdir(dir)
    test.addCleanup(os.chdir, old)


def in_repo(test: unittest.TestCase) -> str:
    """A temporary repo, the folder Claude Code runs a Hook in, with Claude Code's user and managed
    settings of its own, none of them there."""
    env(test)
    dir = testkit.repo(test)
    own = testkit.tempdir(test)
    os.environ.update({
        "CLAUDE_PROJECT_DIR": dir,
        "CLAUDE_PLUGIN_DATA": testkit.tempdir(test),
        "CLAUDE_CONFIG_DIR": own,
        "BALOO_MANAGED_SETTINGS": os.path.join(own, "managed-settings.json"),
        "CLAUDE_PLUGIN_ROOT": PLUGIN,
    })
    return dir


def run(*args: str, stdin: str = "") -> Tuple[int, str, str]:
    """Runs the command `args` with `stdin`, and returns its exit code and what it printed."""
    stdout, stderr = io.StringIO(), io.StringIO()
    code = cli.main(list(args), io.StringIO(stdin), stdout, stderr)
    return code, stdout.getvalue(), stderr.getvalue()


def start(test: unittest.TestCase) -> Tuple[int, str, str]:
    """Runs session-start, and returns its exit code, what it tells Claude, its JSON's
    additionalContext, and its stderr; it fails the test when it prints anything but that JSON."""
    code, out, err = run("session-start")
    if not out:
        return code, "", err
    try:
        context = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError) as e:
        test.fail(f"session-start printed {out!r}, not the Hook's JSON: {e}")
    return code, context, err


def write(path: str, text: str, mode: int = 0o644) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, mode)


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def outside_repo(test: unittest.TestCase) -> str:
    """A temporary folder in no repo; the test is skipped where the temporary folders are inside
    one."""
    dir = testkit.tempdir(test)
    d = dir
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".git")):
            test.skipTest("the temporary folders are inside a repo")
        d = os.path.dirname(d)
    return dir
