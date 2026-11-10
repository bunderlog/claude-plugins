import json
import os
import unittest

from bagheera import doctor, names, review, version
from tests import testkit
from tests.bagheera import commands, test_review
from tests.bagheera.commands import PLUGIN, in_repo, run, set_up, start, write


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
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        for want in [
            "bagheera " + version.read() + " doctor in " + dir + "\n\nNo problems.\n",
            "\nPlugin:\n  running  " + PLUGIN + " (" + version.read() + ")\n",
            "  link     " + link + " -> " + PLUGIN + "\n",
            "no-secrets-in-context  on\n",
        ]:
            self.assertIn(want, out)

    # doctor names each problem, first, with what fixes it, and fails; it changes nothing.
    def test_problems(self):
        dir = in_repo(self)
        self.assertEqual(start(self)[0], 0)
        config = os.path.join(dir, names.OLD_CONFIG)
        write(config, "claude-hooks:\n  no-git-hook-bypass: false\n")
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        os.remove(link)
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        for want in [
            "\nProblems:\n- ",
            "- " + link + " is missing, so the Status line runs nothing",
            "- " + config + " is no longer read: baloo has no settings of its own, so remove it\n",
            "no-git-hook-bypass     on\n",
        ]:
            self.assertIn(want, out)
        self.assertFalse(os.path.lexists(link), "doctor put the link back")

    # doctor names the Output style and the Status line an earlier Release wrote into the clone's
    # settings.local.json, and not a person's own there (PRD no-config).
    def test_left_in_local(self):
        dir = in_repo(self)
        self.assertEqual(start(self)[0], 0)
        local = os.path.join(dir, names.LOCAL_SETTINGS)
        write(local, json.dumps({
            "outputStyle": "baloo:short-replies",
            "statusLine": {"type": "command", "command": "x status-line # managed by baloo"},
        }))
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        self.assertIn("- " + local + " has the statusLine an earlier baloo wrote", out)
        self.assertIn("- " + local + " has the outputStyle an earlier baloo picked", out)
        write(local, json.dumps({
            "outputStyle": "Explanatory", "statusLine": {"type": "command", "command": "mine"},
        }))
        code, out = doctor_run(self)
        self.assertNotIn(local + " has", out)

    # Once session start has seen the Session reviews end, doctor shows how many failed this week
    # and what they all cost.
    def test_session_review_week(self):
        test_review.entrypoint(self, "cli")
        dir = in_repo(self)
        set_up(dir)
        data = os.environ["CLAUDE_PLUGIN_DATA"]
        for session, reply in [
            ("s1", '{"is_error":true,"subtype":"error_max_budget_usd","total_cost_usd":3.1}'),
            ("s2", '{"is_error":false,"result":"P1 adds Order.","total_cost_usd":0.45}'),
        ]:
            claude, _ = test_review.fake_claude(self, reply)
            transcript = test_review.turn("a" * 3000)
            self.assertTrue(review.start(claude, PLUGIN, dir, data, session, transcript))
            test_review.wait(self, dir, data)
        self.assertEqual(start(self)[0], 0)
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"\n  failed this week +1\n  cost this week +\$3\.55\n")

    # A newer version installed for this project than the one running is a problem a restart
    # fixes: Claude Code loads a plugin only when it starts. Another project's install, an older
    # one or a file of another shape is none; a user's install counts where the project has none.
    def test_installed_newer(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        installed = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "plugins", "installed_plugins.json")
        want = (
            f"- this session runs bagheera {version.read()}, but 99.0.0 is installed for this "
            "project: restart Claude Code to run it\n"
        )

        def entry(scope, version, project=""):
            e = {"scope": scope, "version": version}
            if project:
                e["projectPath"] = project
            return e

        for entries, problem in [
            ([entry("local", "99.0.0", dir)], True),
            ([entry("user", "99.0.0")], True),
            ([entry("user", "99.0.0"), entry("project", "0.0.1", dir)], False),
            ([entry("local", "99.0.0", "/elsewhere")], False),
            ([entry("local", "0.0.1", dir)], False),
            ("not a list", False),
        ]:
            with self.subTest(entries=entries):
                write(installed, json.dumps({"plugins": {names.PLUGIN_ID: entries}}))
                code, out = doctor_run(self)
                self.assertEqual((code, want in out), (1 if problem else 0, problem), out)
        write(installed, "{")
        self.assertEqual(doctor_run(self)[0], 0)

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
            "- " + link + " points at " + old + ", not at this plugin, so the Status line runs "
            "that one: the next session start points it here\n", out
        )

    # Outside a repo, doctor says no Config is read, and shows the Checks a Hook runs on by
    # default.
    def test_outside_repo(self):
        in_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = commands.outside_repo(self)
        _, out = doctor_run(self)
        self.assertIn("no-secrets-in-context  on\n", out)
        self.assertNotIn("Git hooks in ", out)

    # Without the plugin's data folder, the link can't be checked: a problem.
    def test_no_data(self):
        in_repo(self)
        del os.environ["CLAUDE_PLUGIN_DATA"]
        code, out = doctor_run(self)
        self.assertEqual(code, 1)
        self.assertIn(
            "- CLAUDE_PLUGIN_DATA is not set, so the link the Status line runs can't be checked: "
            "run doctor as the doctor skill does\n", out
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
