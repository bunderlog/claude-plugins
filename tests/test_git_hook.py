import os
import subprocess
import unittest

from baloo import names
from tests import commands, testkit
from tests.commands import PLUGIN, RUN, write


def commit(dir, message):
    """Commits nothing with the message `message` in the repo `dir`, and returns git's output and
    whether it committed."""
    p = subprocess.run(
        ["git", "-C", dir, "commit", "-q", "--allow-empty", "-m", message],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return p.stdout, p.returncode == 0


def session_start(test, dir, data):
    """Runs the entry script's session-start for the repo `dir` with the data folder `data`, as
    the SessionStart Hook does, and returns what it printed."""
    p = subprocess.run(
        ["python3", "-E", "-s", RUN, "session-start"], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env=dict(os.environ, CLAUDE_PROJECT_DIR=dir, CLAUDE_PLUGIN_DATA=data,
                 CLAUDE_CONFIG_DIR=testkit.tempdir(test), CLAUDE_PLUGIN_ROOT=PLUGIN),
    )
    test.assertEqual(p.returncode, 0, p.stdout)
    return p.stdout


class GitHooks(unittest.TestCase):
    def setUp(self):
        commands.env(self)

    # Session start writes no Git hook, and one an earlier Release wrote lets each commit through,
    # saying that the plugin no longer checks it and how to remove it (ADR git-hooks).
    def test_an_old_git_hook_lets_commits_through(self):
        dir = testkit.repo(self)
        write(os.path.join(dir, names.CONFIG), "git-hooks:\n  conventional-commits: true\n")
        session_start(self, dir, testkit.tempdir(self))
        hooks = os.path.join(dir, ".git", "hooks")
        self.assertEqual([f for f in os.listdir(hooks) if not f.endswith(".sample")], [])
        write(os.path.join(hooks, "commit-msg"),
              "#!/bin/sh\n# managed by baloo: runs the plugin's Checks, rewritten at each session start\n"
              f"exec python3 -E -s '{RUN}' git-hook commit-msg \"$@\"\n", 0o755)
        out, ok = commit(dir, "Add x")
        self.assertTrue(ok, out)
        self.assertIn("baloo: no longer checks commits, hathi does", out)
        self.assertIn("rm .git/hooks/commit-msg", out)


if __name__ == "__main__":
    unittest.main()
