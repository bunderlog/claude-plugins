import os
import subprocess
import unittest

from tests import testkit


class GitHooks(unittest.TestCase):
    # A Git hook an earlier Release wrote finds no run.py behind its link now that baloo ships no
    # Python, and lets the commit through, saying so (ADR git-hooks).
    def test_an_old_git_hook_lets_commits_through(self):
        dir = testkit.repo(self)
        link = os.path.join(testkit.tempdir(self), "bin")
        os.symlink(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.realpath(__file__)))), "plugins", "baloo"), link)
        hook = os.path.join(dir, ".git", "hooks", "commit-msg")
        with open(hook, "w", encoding="utf-8") as f:
            # As v0.35.0's githooks.py wrote it.
            f.write(
                "#!/bin/sh\n"
                "# managed by baloo: runs the plugin's Checks, rewritten at each session start\n"
                f"b='{link}'\n"
                '[ -f "$b/scripts/run.py" ] || '
                "{ echo \"baloo: $b is missing, so the plugin's Checks didn't run\" >&2; exit 0; }\n"
                'exec python3 -E -s "$b/scripts/run.py" git-hook commit-msg "$@"\n'
            )
        os.chmod(hook, 0o755)
        p = subprocess.run(
            ["git", "-C", dir, "commit", "-q", "--allow-empty", "-m", "Add x"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn(f"baloo: {link} is missing", p.stdout)


if __name__ == "__main__":
    unittest.main()
