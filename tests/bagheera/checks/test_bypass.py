import os
import subprocess
import tempfile
import unittest

from bagheera.checks import no_git_hook_bypass

NO_VERIFY = "git commit --no-verify bypasses the Git hooks"
HOOKS_PATH = "git config core.hooksPath changes where the Git hooks are"
HUSKY = "HUSKY=0 turns the Git hooks off"
ENV = "GIT_CONFIG_* setting core.hooksPath bypasses the Git hooks"


class NoGitHookBypass(unittest.TestCase):
    def test_denies_a_bypass(self):
        for command, want in {
            "git commit --no-verify -m x": NO_VERIFY,
            "git commit -n -m x": NO_VERIFY,
            "git commit -anm x": NO_VERIFY,
            "git push --no-verify": "git push --no-verify bypasses the Git hooks",
            "git merge --no-verify feature": "git merge --no-verify bypasses the Git hooks",
            "git -C src commit --no-verify": NO_VERIFY,
            "git --git-dir .git commit --no-verify": NO_VERIFY,
            "/usr/bin/git commit --no-verify": NO_VERIFY,
            "git -c core.hooksPath=/dev/null commit -m x": "git -c core.hooksPath=… bypasses the Git hooks",
            "git -c core.hookspath=/dev/null push": "git -c core.hooksPath=… bypasses the Git hooks",
            "git config core.hooksPath /dev/null": HOOKS_PATH,
            "git config --local core.hooksPath x": HOOKS_PATH,
            "git config core.hooksPath x 2>/dev/null": HOOKS_PATH,
            "git config set core.hooksPath x": HOOKS_PATH,
            "git config --unset core.hooksPath": HOOKS_PATH,
            "git config unset core.hooksPath": HOOKS_PATH,
            "HUSKY=0 git commit -m x": HUSKY,
            "env HUSKY=0 git push": HUSKY,
            "export HUSKY=0": HUSKY,
            'cd src && git commit -m "a; b" --no-verify': NO_VERIFY,
            "make && git push --no-verify | cat": "git push --no-verify bypasses the Git hooks",
            'bash -c "git commit --no-verify"': NO_VERIFY,
            "eval git commit --no-verify": NO_VERIFY,
            "sudo -u me git commit --no-verify": NO_VERIFY,
            "echo $(git commit --no-verify)": NO_VERIFY,
            "git commit --no-verify\ngit push": NO_VERIFY,
            "git commit -m 'x' \\\n --no-verify": NO_VERIFY,
            'echo "$(git commit --no-verify)"': NO_VERIFY,
            'echo "`git commit --no-verify`"': NO_VERIFY,
            "timeout 60 git commit --no-verify": NO_VERIFY,
            "timeout -s KILL 60 git commit --no-verify": NO_VERIFY,
            "nice -n 5 git commit --no-verify": NO_VERIFY,
            "stdbuf -oL git commit --no-verify": NO_VERIFY,
            "git commit --no-veri -m x": NO_VERIFY,
            "git config --file .git/config core.hooksPath /dev/null": HOOKS_PATH,
            "git config -f .git/config core.hooksPath /dev/null": HOOKS_PATH,
            "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0=x git commit": ENV,
            "export GIT_CONFIG_KEY_0=core.hookspath": ENV,
            "GIT_CONFIG_PARAMETERS=\"'core.hooksPath'='x'\" git push": ENV,
        }.items():
            with self.subTest(command=command):
                self.assertEqual(no_git_hook_bypass(command), want)

    def test_allows_what_bypasses_nothing(self):
        for command in [
            "git commit -m x",
            "git commit -m 'skip it with --no-verify'",
            'git commit -m "HUSKY=0"',
            "echo git commit --no-verify",
            "git clean -n",
            "git add -n .",
            "git config core.hooksPath",
            "git config --get core.hooksPath",
            "git config --get core.hooksPath 2>&1",
            "git config core.hooksPath 2>/dev/null",
            "git config core.hooksPath > out",
            "git config get core.hooksPath",
            "git config --list",
            "git config user.name me",
            "git -c user.name=me commit -m x",
            "HUSKY=1 git commit -m x",
            "grep -r no-verify .",
            "echo '$(git commit --no-verify)'",
            'echo "\\$(git commit --no-verify)"',
            "git commit --no-ver -m x",
            "git config -f x --get core.hooksPath",
            "timeout 60 make test",
            "GIT_CONFIG_KEY_0=user.name git commit -m x",
            "",
        ]:
            with self.subTest(command=command):
                self.assertEqual(no_git_hook_bypass(command), "")


    def test_allows_turning_the_repos_own_hooks_on(self):
        # ADR checks: core.hooksPath set in the clone to a hooks folder that is in the repo.
        with tempfile.TemporaryDirectory() as dir:
            _repo(dir, ".githooks", os.path.join(".husky", "_"), "src")
            src = os.path.join(dir, "src")
            for command, cwd in [
                ("git config core.hooksPath .githooks", dir),
                ("git config --local core.hooksPath .githooks", dir),
                ("git config set core.hooksPath ./.githooks/", dir),
                ("git config core.hooksPath .githooks 2>/dev/null", dir),
                ("git config core.hooksPath .husky/_", dir),
                ("git config core.hooksPath .githooks", src),
                ("git -C .. config core.hooksPath .githooks", src),
                ("git config core.hooksPath .githooks && git commit -m x", dir),
            ]:
                with self.subTest(command=command, cwd=cwd):
                    self.assertEqual(no_git_hook_bypass(command, cwd), "")

    def test_denies_any_other_write_of_hooks_path(self):
        with tempfile.TemporaryDirectory() as dir:
            _repo(dir, ".githooks")
            for command in [
                "git config core.hooksPath .husky/_",
                "git config core.hooksPath hooks",
                "git config core.hooksPath /dev/null",
                "git config --global core.hooksPath .githooks",
                "git config --system core.hooksPath .githooks",
                "git config --worktree core.hooksPath .githooks",
                "git config --file .git/config core.hooksPath .githooks",
                "git config --add core.hooksPath .githooks",
                "git config --unset core.hooksPath",
                "git -C /tmp config core.hooksPath .githooks",
                "git --git-dir .git config core.hooksPath .githooks",
                "cd /tmp && git config core.hooksPath .githooks",
                "git -c core.hooksPath=.githooks commit -m x",
                "git -c core.hooksPath=/dev/null rev-parse --git-path hooks",
            ]:
                with self.subTest(command=command):
                    self.assertNotEqual(no_git_hook_bypass(command, dir), "")
            self.assertEqual(no_git_hook_bypass("git config core.hooksPath .githooks"), HOOKS_PATH)
            with tempfile.TemporaryDirectory() as outside:
                os.makedirs(os.path.join(outside, ".githooks"))
                self.assertEqual(
                    no_git_hook_bypass("git config core.hooksPath .githooks", outside), HOOKS_PATH
                )


if __name__ == "__main__":
    unittest.main()


class HooksFolder(unittest.TestCase):
    def test_denies_a_hooks_folder_git_doesnt_track(self):
        # A folder just made, empty or with an untracked file, would turn every Git hook off.
        with tempfile.TemporaryDirectory() as dir:
            _repo(dir)
            os.makedirs(os.path.join(dir, ".githooks"))
            self.assertEqual(no_git_hook_bypass("git config core.hooksPath .githooks", dir), HOOKS_PATH)
            with open(os.path.join(dir, ".githooks", "pre-commit"), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            self.assertEqual(no_git_hook_bypass("git config core.hooksPath .githooks", dir), HOOKS_PATH)
            subprocess.run(["git", "-C", dir, "add", ".githooks"], check=True)
            self.assertEqual(no_git_hook_bypass("git config core.hooksPath .githooks", dir), "")


def _repo(dir, *folders):
    """A git repo at `dir` with each of `folders`, a hook of it tracked."""
    subprocess.run(["git", "init", "-q", dir], check=True)
    for folder in folders:
        os.makedirs(os.path.join(dir, folder))
        with open(os.path.join(dir, folder, "pre-commit"), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        subprocess.run(["git", "-C", dir, "add", folder], check=True)
