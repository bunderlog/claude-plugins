import json
import os
import unittest
from unittest import mock

from bagheera import doctor, failure, names, review, version
from tests import testkit
from tests.bagheera import commands, test_cli, test_review
from tests.bagheera.commands import PLUGIN, in_repo, run, set_up, start, write


def doctor_run(test):
    """Runs doctor and returns its exit code and what it printed, failing the test when it writes
    to stderr."""
    code, out, err = run("doctor")
    test.assertEqual(err, "")
    return code, out


def problem_lines(out):
    """The `- ` lines under doctor's `Problems:`, each a problem."""
    lines = out.split("Problems:\n", 1)[1].splitlines() if "Problems:\n" in out else []
    got = []
    for line in lines:
        if not line.startswith("- "):
            break
        got.append(line)
    return got


class Doctor(unittest.TestCase):
    # After session start, doctor finds no problem and shows what is on, and why.
    def test_doctor(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        key = len(names.BUILD_ID) + 2  # the block's widest key, so every line lines up under it
        for want in [
            "bagheera " + version.read() + " doctor in " + dir + "\n\nNo problems.\n",
            "\nPlugin:\n  " + "running".ljust(key) + PLUGIN + " (" + version.read() + ")\n",
            "  " + names.KNOWLEDGE_ID.ljust(key) + version.read() + "\n",
            "  " + "link".ljust(key) + link + " -> " + PLUGIN + "\n",
            "no-secrets-in-context  on\n",
            "no-hidden-characters   on\n",
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
                commands.installed(dir, **{names.PLUGIN_ID: entries})
                code, out = doctor_run(self)
                self.assertEqual((code, want in out), (1 if problem else 0, problem), out)
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "plugins", "installed_plugins.json"),
              "{")
        self.assertEqual(doctor_run(self)[0], 0)

    # A plugin the repo turns on that Claude Code has no install of for it, or has an install of
    # from an older Release, is a problem, since the project doesn't get what it turned on; with no
    # record of any install, doctor says nothing of any plugin's version (PRD setup).
    def test_project_plugins(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        def entry(v, project=dir, scope="project"):
            return {"scope": scope, "version": v, "projectPath": project}

        missing = (f"- {names.BUILD_ID} is turned on with no install of it for this project: "
                   "/bagheera:setup fixes it\n")
        stale = (f"- {names.BUILD_ID} 0.0.1 is installed, older than the {version.read()} this "
                 "machine has: /bagheera:setup fixes it\n")
        for louie, wanted in [
            ([], missing),
            ([entry("0.0.1", project="/elsewhere")], missing),
            ([entry("0.0.1")], stale),
            ([entry("0.0.1", project="/elsewhere"), entry("0.0.1", "", "user")], stale),
            ([entry(version.read())], ""),
            ([entry("99.0.0")], ""),
        ]:
            with self.subTest(louie=louie):
                commands.installed(dir, **{names.BUILD_ID: louie})
                code, out = doctor_run(self)
                self.assertEqual((code, missing in out, stale in out),
                                 (1 if wanted else 0, wanted == missing, wanted == stale), out)
                # The fix is setup's, never one the person types: not /plugin, not claude plugin.
                if wanted:
                    self.assertIn(wanted.rstrip("\n"), problem_lines(out))
                for line in problem_lines(out):
                    self.assertNotIn("/plugin ", line)
                    self.assertNotIn("claude plugin update", line)
        # A key set to false isn't turned on, so neither problem is its; setting a project up turns
        # both on, so the repo now lacks that item instead, which is setup's problem, not this one.
        with open(os.path.join(dir, names.PROJECT_SETTINGS), encoding="utf-8") as f:
            fields = json.load(f)
        fields["enabledPlugins"] = {names.KNOWLEDGE_ID: True, names.BUILD_ID: False}
        write(os.path.join(dir, names.PROJECT_SETTINGS), json.dumps(fields))
        commands.installed(dir, **{names.BUILD_ID: []})
        out = doctor_run(self)[1]
        self.assertNotIn(missing, out)
        self.assertNotIn(names.BUILD_ID + " 0.0.1", out)

    # Git hooks the repo tracks that its clone hasn't turned on are a problem, with /bagheera:setup
    # as the fix; with core.hooksPath set to their folder, they aren't (PRD setup).
    def test_hooks_off(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        testkit.git(dir, "add", ".githooks")
        off = "- its Git hooks are off in this clone: /bagheera:setup fixes it"
        code, out = doctor_run(self)
        self.assertEqual((code, problem_lines(out)), (1, [off]), out)
        testkit.git(dir, "config", "core.hooksPath", ".githooks")
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        self.assertNotIn(off, out)

    # doctor names each of setup.needs a problem, with /bagheera:setup, and nothing else of what
    # setup fixes; a repo that isn't set up gets one line for its items (PRD setup).
    def test_setup_needs(self):
        dir = in_repo(self)
        self.assertEqual(start(self)[0], 0)
        out = doctor_run(self)[1]
        self.assertEqual([line for line in problem_lines(out) if "/bagheera:setup" in line],
                         [f"- {dir} isn't set up for bunderlog's plugins: /bagheera:setup sets it "
                          "up"])
        set_up(dir)
        testkit.git(dir, "add", ".githooks")
        with open(os.path.join(dir, names.PROJECT_SETTINGS), encoding="utf-8") as f:
            fields = json.load(f)
        del fields["attribution"]
        write(os.path.join(dir, names.PROJECT_SETTINGS), json.dumps(fields))
        commands.installed(dir, **{names.BUILD_ID: []})
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        self.assertEqual([line for line in problem_lines(out) if "/bagheera:setup" in line], [
            "- attribution off in .claude/settings.json is missing: /bagheera:setup fixes it",
            "- louie@bunderlog is turned on with no install of it for this project: "
            "/bagheera:setup fixes it",
            "- its Git hooks are off in this clone: /bagheera:setup fixes it",
        ])

    # With no record of what is installed, doctor says nothing of any plugin's version: the file is
    # Claude Code's and undocumented, so an unreadable one is no evidence of anything (ADR doctor).
    def test_no_records(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        installed = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "plugins",
                                 "installed_plugins.json")
        for text in ["{", json.dumps({"plugins": []}), ""]:
            with self.subTest(text=text):
                write(installed, text)
                code, out = doctor_run(self)
                self.assertEqual(code, 0, out)
                self.assertNotIn(names.BUILD_ID, out)
        os.remove(installed)
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        self.assertNotIn(names.BUILD_ID, out)

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

    # A Check that raises lets the call through, and doctor names it, where in the plugin's code
    # it failed, but no word of the call, until another version runs (ADR checks).
    def test_check_failed(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        secret = "cat .env.s3cr3t"
        with mock.patch("bagheera.checks.no_secrets_in_context", side_effect=KeyError(secret)):
            self.assertEqual(run("pre-tool-use", stdin=test_cli.bash(secret)), (0, "", ""))
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        self.assertRegex(
            out, r"\n- bagheera:no-secrets-in-context failed on a Bash call at [0-9: -]+ "
            r"\(KeyError at bagheera/cli\.py:\d+\) and let it through: report it at "
            r"https://github\.com/bunderlog/claude-plugins/issues; the Release that fixes it "
            r"stops showing this\n"
        )
        self.assertNotIn("s3cr3t", out)
        kept = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], failure.FILE)
        with open(kept, encoding="utf-8") as f:
            self.assertNotIn("s3cr3t", f.read())
        with open(kept, encoding="utf-8") as f:
            failed = json.load(f)
        write(kept, json.dumps(dict(failed, version="0.0.1")))
        self.assertEqual(doctor_run(self)[0], 0)

    # A failure of no-hidden-characters is named as the other Checks' are (PRD hidden-characters).
    def test_hidden_characters_failed(self):
        set_up(in_repo(self))
        self.assertEqual(start(self)[0], 0)
        call = '{"tool_name": "Write", "tool_input": {"file_path": "a.py", "content": "a"}}'
        with mock.patch("bagheera.checks.no_hidden_characters", side_effect=KeyError("a")):
            self.assertEqual(run("pre-tool-use", stdin=call), (0, "", ""))
        code, out = doctor_run(self)
        self.assertEqual(code, 1, out)
        self.assertIn("\n- bagheera:no-hidden-characters failed on a Write call at ", out)

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


class Machine(unittest.TestCase):
    # doctor lists the machine's projects that need attention, each thing with what to do, and
    # counts the rest; another project's needs aren't its problems, so it still exits 0, in a repo
    # or outside one (PRD visibility).
    def test_machine(self):
        dir = in_repo(self)
        set_up(dir)
        self.assertEqual(start(self)[0], 0)
        other = testkit.repo(self)
        write(os.path.join(other, names.INBOX), "## A\n\n2026-11-10 · session\n")
        quiet = testkit.repo(self)
        folder = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects")
        for name, cwd in [("o", other), ("q", quiet)]:
            write(os.path.join(folder, name, "s.jsonl"), json.dumps({"type": "user", "cwd": cwd}) + "\n")
        code, out = doctor_run(self)
        self.assertEqual(code, 0, out)
        self.assertIn(f"  {other}:\n    - 1 Inbox item not gone through: /baloo:inbox there\n", out)
        self.assertIn("  need nothing  1\n  not set up    2\n", out)
        commands.chdir(self, testkit.tempdir(self))
        del os.environ["CLAUDE_PROJECT_DIR"]
        code, out = doctor_run(self)
        self.assertIn(f"  {other}:\n", out)

    def test_none_found(self):
        in_repo(self)
        self.assertIn("days:\n  none found\n", doctor_run(self)[1])


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
