"""Temporary git repos for tests, cut off from the machine's git: no config of the machine's
applies, commits are unsigned, and no GIT_ variable the tests ran with, such as the GIT_DIR or
GIT_INDEX_FILE of a Git hook that runs them, reaches git."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


def tempdir(test: unittest.TestCase) -> str:
    """A new empty folder, removed when the test `test` ends."""
    path = os.path.realpath(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, path, ignore_errors=True)
    return path


def repo(test: unittest.TestCase) -> str:
    """A new repo in a temporary folder, on the branch main, for the test `test`; until the test
    ends, git run by it or by the code it tests sees only the environment repo sets."""
    patcher = mock.patch.dict(os.environ)
    patcher.start()
    test.addCleanup(patcher.stop)  # puts the environment back when the test ends
    for k in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[k]
    os.environ.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
        }
    )
    dir = tempdir(test)
    git(dir, "init", "-q", "-b", "main")
    return dir


def git(dir: str, *args: str) -> str:
    """What git, run in `dir` with `args`, prints, stdout and stderr; it fails the test when git
    fails."""
    p = subprocess.run(
        ["git", "-C", dir, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if p.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: exit status {p.returncode}\n{p.stdout}")
    return p.stdout
