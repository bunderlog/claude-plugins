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


if __name__ == "__main__":
    unittest.main()
