import os
import unittest

from baloo import doctor, names, version
from tests import commands, testkit
from tests.commands import PLUGIN, in_repo, read, run, start, write


def doctor_run(test):
    """Runs doctor and returns its exit code and what it printed, failing the test when it writes
    to stderr."""
    code, out, err = run("doctor")
    test.assertEqual(err, "")
    return code, out


class Doctor(unittest.TestCase):
    # After session start, doctor finds no problem and shows what is on, and why.
    def test_doctor(self):
        dir = in_repo(self)
        self.assertEqual(start(self)[0], 0)
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        for want in [
            "baloo " + version.read() + " doctor in " + dir + "\n\nNo problems.\n",
            "\nPlugin:\n  running  " + PLUGIN + " (" + version.read() + ")\n",
            "  link     " + link + " -> " + PLUGIN + "\n",
            "Config: " + os.path.join(dir, names.CONFIG) + "\n",
            "no-secrets-in-context  on\n",
            "commit-msg  running: no-ai-coauthor, conventional-commits\n",
            "Guidelines:\n",
        ]:
            self.assertIn(want, out)

    # doctor names each problem, first, with what fixes it, and fails; it changes nothing.
    def test_problems(self):
        dir = in_repo(self)
        self.assertEqual(start(self)[0], 0)
        config = os.path.join(dir, names.CONFIG)
        # The template's own claude-hooks turns the Check off, since a key twice isn't read.
        text = read(config).replace("  no-git-hook-bypass: true\n", "  no-git-hook-bypass: false\n")
        write(config, text + "nope: 1\nstop-check: make\n")
        theirs = os.path.join(dir, ".git", "hooks", "pre-commit")
        write(theirs, "#!/bin/sh\nnpm test\n", 0o755)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        os.remove(link)
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        checks = "no-secrets-in-commits, no-stale-adr-date, no-conflict-markers, no-large-files"
        for want in [
            "\nProblems:\n- ",
            "- " + link + " is missing, so the Git hooks and the Status line run nothing",
            "- " + theirs + " is not the plugin's Git hook, so " + checks + " don't run",
            "nope is not a setting; ignored\n",
            "stop-check is no longer a setting and is ignored: delete it\n",
            "no-git-hook-bypass     off\n",
            "pre-commit  theirs: " + checks + "\n",
        ]:
            self.assertIn(want, out)
        self.assertFalse(os.path.lexists(link), "doctor put the link back")

    # A link that points elsewhere, such as at the version before, is a problem.
    def test_link_elsewhere(self):
        in_repo(self)
        self.assertEqual(start(self)[0], 0)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        old = testkit.tempdir(self)
        os.remove(link)
        os.symlink(old, link)
        code, out = doctor_run(self)
        self.assertEqual(code, 1)
        self.assertIn(
            "- " + link + " points at " + old + ", not at this plugin, so the Git hooks and the "
            "Status line run that one: the next session start points it here\n", out
        )

    # Outside a repo, doctor says no Config is read, and shows the Checks a Hook runs on by
    # default.
    def test_outside_repo(self):
        in_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = commands.outside_repo(self)
        _, out = doctor_run(self)
        for want in [
            "Config: none, outside a repo",
            "no-secrets-in-context  on, by default\n",
            "linear-history         off, by default\n",
        ]:
            self.assertIn(want, out)
        self.assertNotIn("Git hooks in ", out)

    # Without the plugin's data folder, the link can't be checked: a problem.
    def test_no_data(self):
        in_repo(self)
        del os.environ["CLAUDE_PLUGIN_DATA"]
        code, out = doctor_run(self)
        self.assertEqual(code, 1)
        self.assertIn(
            "- CLAUDE_PLUGIN_DATA is not set, so the link the Git hooks run can't be checked: run "
            "doctor as the doctor skill does\n", out
        )


class Columns(unittest.TestCase):
    # Each run of lines with a tab aligns its first cells two spaces past the widest, as Go's
    # tabwriter did; a line without one ends the run.
    def test_columns(self):
        self.assertEqual(
            doctor._columns("\nA:\n  ab\tx\n  abcd\ty: z\nB:\n  a\tq\n"),
            "\nA:\n  ab    x\n  abcd  y: z\nB:\n  a  q\n",
        )


if __name__ == "__main__":
    unittest.main()
