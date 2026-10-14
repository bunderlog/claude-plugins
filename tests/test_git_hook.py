import os
import subprocess
import unittest

from baloo import names
from tests import commands, testkit
from tests.commands import PLUGIN, RUN, read, write


def commit(dir, message):
    """Commits nothing with the message `message` in the repo `dir`, and returns git's output and
    whether it committed."""
    p = subprocess.run(
        ["git", "-C", dir, "commit", "-q", "--allow-empty", "-m", message],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return p.stdout, p.returncode == 0


def husky9(dir):
    """Makes the repo `dir` one whose Git hooks husky 9 runs, as `husky init` leaves it."""
    for name, text in {
        "h": '#!/usr/bin/env sh\nn=$(basename "$0")\ns=$(dirname "$(dirname "$0")")/$n\n'
             '[ ! -f "$s" ] && exit 0\nsh -e "$s" "$@"\n',
        "commit-msg": '#!/usr/bin/env sh\n. "$(dirname "$0")/h"\n',
    }.items():
        write(os.path.join(dir, ".husky", "_", name), text, 0o755)
    testkit.git(dir, "config", "core.hooksPath", ".husky/_")


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

    # Session start writes the Git hooks, and git runs the Checks the Config turns on through
    # them, with husky 9 too; once the link is gone, a Git hook passes and says so.
    def test_run_the_checks(self):
        for husky in [False, True]:
            with self.subTest(husky=husky):
                dir = testkit.repo(self)
                if husky:
                    husky9(dir)
                write(os.path.join(dir, names.CONFIG), "git-hooks:\n  conventional-commits: true\n")
                data = testkit.tempdir(self)
                self.assertIn("wrote the Git hooks commit-msg in ", session_start(self, dir, data))
                out, ok = commit(dir, "Add x")
                self.assertFalse(ok, out)
                self.assertIn("baloo:conventional-commits: ", out)
                out, ok = commit(dir, "feat: x")
                self.assertTrue(ok, out)
                os.remove(os.path.join(data, names.PLUGIN))
                out, ok = commit(dir, "Add y")
                self.assertTrue(ok, out)
                self.assertIn("is missing, so the plugin's Checks didn't run", out)

    # A Git hook runs the command the Config sets for it once its Checks pass, with git's
    # arguments, and the commit fails when the command does; where a Check fails, the command
    # doesn't run.
    def test_run_the_commands(self):
        dir = testkit.repo(self)
        write(os.path.join(dir, names.CONFIG), (
            "git-hooks:\n  conventional-commits: true\ngit-hook-commands:\n"
            '  commit-msg: grep -q feat "$1" && echo ran >> ran\n'
            "  pre-commit: test ! -e fail\n"
        ))
        data = testkit.tempdir(self)
        self.assertIn(
            "wrote the Git hooks commit-msg, pre-commit in ", session_start(self, dir, data)
        )
        ran = os.path.join(dir, "ran")
        out, ok = commit(dir, "feat: x")
        self.assertEqual((ok, read(ran)), (True, "ran\n"), out)
        out, ok = commit(dir, "Add y")
        self.assertEqual((ok, read(ran)), (False, "ran\n"), out)
        write(os.path.join(dir, "fail"), "")
        out, ok = commit(dir, "feat: z")
        self.assertFalse(ok, out)
        self.assertIn("baloo:git-hook-commands.pre-commit: ", out)

    # pre-push's command gets the pushed refs on stdin, after linear-history has read them.
    def test_pre_push_command_gets_the_refs(self):
        dir = testkit.repo(self)
        write(os.path.join(dir, names.CONFIG), (
            "git-hooks:\n  linear-history: true\ngit-hook-commands:\n  pre-push: cat > pushed\n"
        ))
        testkit.git(dir, "commit", "-q", "--allow-empty", "-m", "feat: x")
        head = testkit.git(dir, "rev-parse", "HEAD").strip()
        refs = "refs/heads/main " + head + " refs/heads/main " + "0" * 40 + "\n"
        p = subprocess.run(
            ["python3", "-E", "-s", RUN, "git-hook", "pre-push", "origin",
             "https://example.com/x.git"],
            cwd=dir, input=refs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(read(os.path.join(dir, "pushed")), refs)


if __name__ == "__main__":
    unittest.main()
