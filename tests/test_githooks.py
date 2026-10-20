import os
import shutil
import subprocess
import unittest

from baloo import githooks
from tests import testkit

ALL = {"no-secrets-in-commits", "no-stale-adr-date", "no-ai-coauthor", "conventional-commits",
       "linear-history"}  # fmt: skip


def on(*names):
    """Turns on the Checks `names`."""
    return lambda name: name in names


def all_on(name):
    return name in ALL


def want_script(data, hook):
    """The Git hook `hook` the plugin writes, running the plugin through the link in `data`."""
    return (
        "#!/bin/sh\n"
        "# managed by baloo: runs the plugin's Checks, rewritten at each session start\n"
        "b='" + os.path.join(data, "baloo") + "'\n"
        '[ -f "$b/scripts/run.py" ] || '
        "{ echo \"baloo: $b is missing, so the plugin's Checks didn't run\" >&2; exit 0; }\n"
        "command -v python3 >/dev/null 2>&1 || "
        "{ echo \"baloo: python3 is missing, so the plugin's Checks didn't run\" >&2; exit 0; }\n"
        'exec python3 -E -s "$b/scripts/run.py" git-hook ' + hook + ' "$@"\n'
    )


# A Git hook as the Go binary wrote it, before the port to Python.
def go_script(data, hook):
    return (
        "#!/bin/sh\n"
        "# managed by baloo: runs the plugin's Checks, rewritten at each session start\n"
        "b='" + os.path.join(data, "baloo") + "'\n"
        '[ ! -x "$b" ] || exec "$b" git-hook ' + hook + ' "$@"\n'
        "echo \"baloo: $b is missing, so the plugin's Checks didn't run\" >&2\n"
    )


def want_husky_line(hook):
    """The line the plugin puts first in husky's `hook`."""
    return (
        'baloo_hook="$(git rev-parse --git-common-dir)/baloo-hooks/' + hook + '"; '
        '[ ! -x "$baloo_hook" ] || "$baloo_hook" "$@" || exit $? # managed by baloo'
    )


def read(path):
    with open(path, newline="") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(text)
    os.chmod(path, 0o755)


def husky9(dir):
    """Makes the repo `dir` one whose Git hooks husky 9 runs, as `husky init` leaves it."""
    write(
        os.path.join(dir, ".husky", "_", "h"),
        '#!/usr/bin/env sh\nn=$(basename "$0")\ns=$(dirname "$(dirname "$0")")/$n\n'
        '[ ! -f "$s" ] && exit 0\nsh -e "$s" "$@"\n',
    )
    write(os.path.join(dir, ".husky", "_", "commit-msg"), '#!/usr/bin/env sh\n. "$(dirname "$0")/h"\n')
    testkit.git(dir, "config", "core.hooksPath", ".husky/_")


class Write(unittest.TestCase):
    def setUp(self):
        self.root, self.data = testkit.repo(self), testkit.tempdir(self)
        self.hooks = os.path.join(self.root, ".git", "hooks")

    def assert_missing(self, path):
        self.assertFalse(os.path.lexists(path), f"{path} is there; want it gone")

    # The plugin writes a Git hook where one of its Checks is on, executable, and leaves the others
    # unwritten; once written, writing again changes nothing.
    def test_writes_the_hooks_whose_checks_are_on(self):
        r, err = githooks.write(self.root, self.data, on("conventional-commits"))
        self.assertIsNone(err)
        self.assertEqual(r, githooks.Report(dir=self.hooks, written=["commit-msg"]))
        path = os.path.join(self.hooks, "commit-msg")
        self.assertEqual(read(path), want_script(self.data, "commit-msg"))
        self.assertTrue(os.stat(path).st_mode & 0o111, "commit-msg isn't executable")
        self.assert_missing(os.path.join(self.hooks, "pre-commit"))
        self.assert_missing(os.path.join(self.hooks, "pre-push"))
        self.assertNotEqual(os.readlink(os.path.join(self.data, "baloo")), "")
        r, err = githooks.write(self.root, self.data, on("conventional-commits"))
        self.assertEqual((r, err), (githooks.Report(dir=self.hooks), None))

    # A Git hook is written where the Config sets its command, though none of its Checks is on, and
    # inspect names the command among what it runs.
    def test_writes_the_hooks_with_a_command(self):
        r, err = githooks.write(self.root, self.data, on("git-hook-commands.pre-commit"))
        self.assertIsNone(err)
        self.assertEqual(r, githooks.Report(dir=self.hooks, written=["pre-commit"]))
        _, _, got = githooks.inspect(
            self.root, self.data, on("no-secrets-in-commits", "git-hook-commands.pre-commit")
        )
        self.assertEqual(got[1].state, githooks.RUNNING)
        self.assertEqual(got[1].runs, ["no-secrets-in-commits", "git-hook-commands.pre-commit"])

    # A Git hook whose Checks are all off is taken out, but only the plugin's own.
    def test_takes_out_its_own(self):
        self.assertIsNone(githooks.write(self.root, self.data, all_on)[1])
        r, err = githooks.write(self.root, self.data, on("linear-history"))
        self.assertIsNone(err)
        self.assertEqual(
            r, githooks.Report(dir=self.hooks, removed=["commit-msg", "pre-commit"])
        )
        self.assert_missing(os.path.join(self.hooks, "commit-msg"))
        self.assertEqual(
            read(os.path.join(self.hooks, "pre-push")), want_script(self.data, "pre-push")
        )

    # A Git hook the plugin didn't write is left alone, and named with the Checks it keeps from
    # running, if any.
    def test_leaves_theirs(self):
        theirs = os.path.join(self.hooks, "pre-commit")
        write(theirs, "#!/bin/sh\nnpm test\n")
        r, err = githooks.write(self.root, self.data, all_on)
        self.assertIsNone(err)
        self.assertEqual(
            r.theirs, [githooks.Blocked(theirs, ["no-secrets-in-commits", "no-stale-adr-date"])]
        )
        self.assertNotIn("pre-commit", r.written)
        self.assertEqual(read(theirs), "#!/bin/sh\nnpm test\n")
        r, err = githooks.write(self.root, self.data, on("linear-history"))
        self.assertIsNone(err)
        self.assertEqual(r.theirs, [])
        self.assertEqual(read(theirs), "#!/bin/sh\nnpm test\n")

    # A Git hook the Go binary wrote is the plugin's: it is rewritten to run the plugin's Python.
    def test_rewrites_one_the_go_binary_wrote(self):
        write(os.path.join(self.hooks, "pre-push"), go_script(self.data, "pre-push"))
        _, _, got = githooks.inspect(self.root, self.data, on("linear-history"))
        self.assertEqual(got[2].state, githooks.OUTDATED)
        self.assertEqual(got[2].link, os.path.join(self.data, "baloo"))
        r, err = githooks.write(self.root, self.data, on("linear-history"))
        self.assertEqual((r, err), (githooks.Report(dir=self.hooks), None))
        self.assertEqual(
            read(os.path.join(self.hooks, "pre-push")), want_script(self.data, "pre-push")
        )

    # Where the Git hooks' folder is in the working tree, each Git hook the plugin writes goes into
    # info/exclude.
    def test_excludes_from_the_working_tree(self):
        testkit.git(self.root, "config", "core.hooksPath", ".githooks")
        r, err = githooks.write(self.root, self.data, on("linear-history"))
        self.assertIsNone(err)
        self.assertEqual(r.written, ["pre-push"])
        self.assertEqual(
            read(os.path.join(self.root, ".githooks", "pre-push")),
            want_script(self.data, "pre-push"),
        )
        self.assertIn(
            "\n/.githooks/pre-push\n", read(os.path.join(self.root, ".git", "info", "exclude"))
        )

    # With husky 9, the plugin's Git hooks go into the git folder's baloo-hooks/, and a line first
    # in husky's own runs each; where a Git hook goes, so does its line, and a file the line was
    # all of.
    def test_husky(self):
        root, data = self.root, self.data
        write(os.path.join(root, ".husky", "_", "h"), "# husky's\n")
        write(os.path.join(root, ".husky", "pre-commit"), "npm test\n")
        write(os.path.join(root, ".husky", "pre-push"), "#!/usr/bin/env sh\nnpm run lint\n")
        testkit.git(root, "config", "core.hooksPath", ".husky/_")
        hooks = ["commit-msg", "pre-commit", "pre-push"]
        husky = [".husky/commit-msg", ".husky/pre-commit", ".husky/pre-push"]
        ours = os.path.join(root, ".git", "baloo-hooks")
        r, err = githooks.write(root, data, all_on)
        self.assertIsNone(err)
        self.assertEqual(r, githooks.Report(dir=ours, written=hooks, husky=husky))
        for hook in hooks:
            self.assertEqual(read(os.path.join(ours, hook)), want_script(data, hook))
            self.assert_missing(os.path.join(root, ".husky", "_", hook))
        for name, want in {
            "commit-msg": want_husky_line("commit-msg") + "\n",
            "pre-commit": want_husky_line("pre-commit") + "\nnpm test\n",
            "pre-push": "#!/usr/bin/env sh\n" + want_husky_line("pre-push") + "\nnpm run lint\n",
        }.items():
            self.assertEqual(read(os.path.join(root, ".husky", name)), want, name)
        self.assertEqual(githooks.write(root, data, all_on), (githooks.Report(dir=ours), None))

        r, err = githooks.write(root, data, on())
        self.assertIsNone(err)
        self.assertEqual(r, githooks.Report(dir=ours, removed=hooks, husky=husky))
        self.assert_missing(os.path.join(root, ".husky", "commit-msg"))
        self.assertEqual(read(os.path.join(root, ".husky", "pre-commit")), "npm test\n")
        self.assertEqual(
            read(os.path.join(root, ".husky", "pre-push")), "#!/usr/bin/env sh\nnpm run lint\n"
        )

    # core.hooksPath at /dev/null, as `claude plugin eval` sets it, turns the Git hooks off: write
    # writes nothing and reports no error.
    def test_hooks_path_at_dev_null(self):
        testkit.git(self.root, "config", "core.hooksPath", os.devnull)
        self.assertEqual(githooks.write(self.root, self.data, all_on), (githooks.Report(), None))

    # Outside a repo, write says why and writes nothing.
    def test_outside_a_repo(self):
        r, err = githooks.write(testkit.tempdir(self), self.data, all_on)
        self.assertEqual(r, githooks.Report())
        self.assertRegex(str(err), r"^git rev-parse: exit status \d+$")


def states(hooks):
    """The state of each Git hook in `hooks`, by name."""
    return {h.name: h.state for h in hooks}


class Inspect(unittest.TestCase):
    # inspect finds each Git hook as it is against what write would make of it, and changes
    # nothing.
    def test_inspect(self):
        root, data = testkit.repo(self), testkit.tempdir(self)
        hooks = os.path.join(root, ".git", "hooks")
        dir, husky, got = githooks.inspect(root, data, all_on)
        self.assertEqual((dir, husky), (hooks, False))
        self.assertEqual(
            states(got),
            {"commit-msg": "missing", "pre-commit": "missing", "pre-push": "missing"},
        )
        self.assertFalse(os.path.lexists(os.path.join(hooks, "commit-msg")))

        self.assertIsNone(githooks.write(root, data, all_on)[1])
        write(os.path.join(hooks, "pre-commit"), "#!/bin/sh\nnpm test\n")
        write(os.path.join(hooks, "pre-push"), want_script(testkit.tempdir(self), "pre-push"))
        _, _, got = githooks.inspect(root, data, all_on)
        self.assertEqual(
            states(got),
            {"commit-msg": "running", "pre-commit": "theirs", "pre-push": "outdated"},
        )
        self.assertEqual(got[0].link, os.path.join(data, "baloo"))
        self.assertEqual(got[1].link, "")
        self.assertEqual(got[0].runs, ["no-ai-coauthor", "conventional-commits"])

        _, _, got = githooks.inspect(root, data, on())
        self.assertEqual(
            states(got),
            {"commit-msg": "leftover", "pre-commit": "off", "pre-push": "leftover"},
        )

    # With husky 9, inspect finds the plugin's Git hooks in the git folder, and a line in husky's
    # own that isn't as session start keeps it.
    def test_husky(self):
        root, data = testkit.repo(self), testkit.tempdir(self)
        write(os.path.join(root, ".husky", "_", "h"), "# husky's\n")
        testkit.git(root, "config", "core.hooksPath", ".husky/_")
        self.assertIsNone(githooks.write(root, data, all_on)[1])
        write(os.path.join(root, ".husky", "pre-push"), "npm run lint\n")
        dir, husky, got = githooks.inspect(root, data, all_on)
        self.assertEqual((dir, husky), (os.path.join(root, ".git", "baloo-hooks"), True))
        for h in got:
            self.assertEqual(h.state, githooks.RUNNING, h.name)
            self.assertEqual(h.husky_outdated, h.name == "pre-push", h.name)


# A plugin folder whose run.py says what it was run with and fails, so a commit shows it.
RUN_PY = "import sys\nsys.stderr.write('run.py ' + ' '.join(sys.argv[1:]) + '\\n')\nsys.exit(1)\n"


class Script(unittest.TestCase):
    """git runs the Git hooks write makes: through them, the plugin's run.py."""

    def setUp(self):
        self.git = shutil.which("git")
        self.data = testkit.tempdir(self)
        self.plugin = testkit.tempdir(self)
        write(os.path.join(self.plugin, "scripts", "run.py"), RUN_PY)

    def repo(self, husky):
        root = testkit.repo(self)
        if husky:
            husky9(root)
        self.assertIsNone(githooks.write(root, self.data, on("conventional-commits"))[1])
        link = os.path.join(self.data, "baloo")
        os.remove(link)
        os.symlink(self.plugin, link)
        return root

    def commit(self, root):
        p = subprocess.run(
            [self.git, "-C", root, "commit", "-q", "--allow-empty", "-m", "x"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return p.stdout, p.returncode == 0

    # The Git hook runs the plugin's run.py with python3, the Git hook's name and git's arguments,
    # and fails when it does, with husky 9 too.
    def test_runs_the_plugin(self):
        for husky in (False, True):
            with self.subTest(husky=husky):
                out, ok = self.commit(self.repo(husky))
                self.assertFalse(ok)
                self.assertIn("run.py git-hook commit-msg .git/COMMIT_EDITMSG", out)

    # Where the link is gone, or python3 isn't on PATH, the Git hook says the Checks didn't run,
    # and passes.
    def test_passes_without_the_plugin(self):
        root = self.repo(False)
        os.environ["PATH"] = testkit.tempdir(self)  # repo puts the environment back
        out, ok = self.commit(root)
        self.assertTrue(ok, out)
        self.assertEqual(out, "baloo: python3 is missing, so the plugin's Checks didn't run\n")
        os.remove(os.path.join(self.data, "baloo"))
        out, ok = self.commit(root)
        self.assertTrue(ok, out)
        self.assertEqual(
            out,
            f"baloo: {self.data}/baloo is missing, so the plugin's Checks didn't run\n",
        )


if __name__ == "__main__":
    unittest.main()
