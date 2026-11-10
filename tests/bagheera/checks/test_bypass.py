import unittest

from baloo.checks import no_git_hook_bypass

NO_VERIFY = "git commit --no-verify bypasses the Git hooks"
HOOKS_PATH = "git config core.hooksPath changes where the Git hooks are"
HUSKY = "HUSKY=0 turns the Git hooks off"


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
            "git config get core.hooksPath",
            "git config --list",
            "git config user.name me",
            "git -c user.name=me commit -m x",
            "HUSKY=1 git commit -m x",
            "grep -r no-verify .",
            "",
        ]:
            with self.subTest(command=command):
                self.assertEqual(no_git_hook_bypass(command), "")


if __name__ == "__main__":
    unittest.main()
