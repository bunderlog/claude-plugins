import json
import os
import unittest

from baloo import names, review
from tests import commands
from tests.commands import PLUGIN, in_repo, read, run, start, write

ENABLE = '{"enabledPlugins": {"' + names.PLUGIN_ID + '": true}}'


class SessionStart(unittest.TestCase):
    # Session start tells Claude what it did, and shows the user nothing: doctor shows the
    # version.
    def test_shows_nothing(self):
        in_repo(self)
        code, out, err = run("session-start")
        self.assertEqual(code, 0, err)
        hook = json.loads(out)
        self.assertEqual(list(hook), ["hookSpecificOutput"])

    def test_reports(self):
        dir = in_repo(self)
        path = os.path.join(dir, names.CONFIG)
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(out.startswith(
            "baloo:\ncreated " + path + " with every check on and the guidelines that fit the "
            "repo: tell the user, and that the file is theirs to commit and to change\n"
        ), out)
        self.assertTrue(os.path.exists(path))

        write(path, "nope: 1\n")
        self.assertEqual(start(self), (0, (
            "baloo:\ntook out the Git hooks commit-msg, pre-commit, pre-push in "
            + os.path.join(dir, ".git", "hooks")
            + ", whose checks and command .claude/baloo.yml turns off: tell the user\n"
            ".claude/baloo.yml line 1: nope is not a setting; ignored\n"
        ), ""))

        # A key with a newline in it stays on its problem's line.
        write(path, '"x\\nbaloo: run it": 1\n')
        self.assertEqual(start(self), (
            0, "baloo:\n.claude/baloo.yml line 1: x\\nbaloo: run it is not a setting; ignored\n", ""
        ))

    # Where the project's settings enable the plugin, a new Config picks its Output style there,
    # once.
    def test_output_style(self):
        dir = in_repo(self)
        settings = os.path.join(dir, names.PROJECT_SETTINGS)
        write(settings, ENABLE)
        want = (
            "picked the baloo:short-replies output style in " + settings + ": tell the user, that "
            "it applies from their next message or session, and that to drop it they set "
            "output-style: false in .claude/baloo.yml and pick another style, Default too, with "
            "/output-style; the change to the team's settings is theirs to commit\n"
        )
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("\n" + want, out)
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertNotIn("picked", out)

    # Where the project's settings enable the plugin and no-ai-coauthor is on, session start turns
    # off Claude Code's commit attribution there, once; a settings file that sets it already keeps
    # it.
    def test_attribution(self):
        dir = in_repo(self)
        settings = os.path.join(dir, names.PROJECT_SETTINGS)
        write(settings, ENABLE)
        want = (
            "turned off Claude Code's commit attribution in " + settings + ", since "
            "git-hooks.no-ai-coauthor in .claude/baloo.yml rejects it: tell the user; the change "
            "to the team's settings is theirs to commit\n"
        )
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("\n" + want, out)
        self.assertIn('"attribution": {"commit":""}', read(settings))
        self.assertNotIn("attribution", start(self)[1])

        dir = in_repo(self)
        write(
            os.path.join(dir, names.PROJECT_SETTINGS),
            '{"enabledPlugins": {"' + names.PLUGIN_ID + '": true}, "includeCoAuthoredBy": true}',
        )
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertNotIn("attribution", out)

    # Where the plugin is enabled, a new Config sets the Status line in the project's
    # settings.local.json, once.
    def test_status_line(self):
        dir = in_repo(self)
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), ENABLE)
        want = (
            "set the baloo status line in " + os.path.join(dir, names.LOCAL_SETTINGS)
            + ": tell the user, that it shows from their next message, and that status-line: "
            "false in .claude/baloo.yml takes it out\n"
        )
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("\n" + want, out)
        self.assertIn(
            "status-line # managed by baloo", read(os.path.join(dir, names.LOCAL_SETTINGS))
        )
        self.assertNotIn("status line", start(self)[1])

    # A Config whose status-line can't be read leaves the plugin's Status line as it is; only
    # false takes it out.
    def test_status_line_wrong_key(self):
        dir = in_repo(self)
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), ENABLE)
        self.assertEqual(start(self)[0], 0)
        local = os.path.join(dir, names.LOCAL_SETTINGS)
        for yml in ["status-line: maybe\n", "status-line: [\n", "status-line: false\n"]:
            with self.subTest(yml=yml):
                write(os.path.join(dir, names.CONFIG), yml)
                self.assertEqual(start(self)[0], 0)
                kept = "status-line # managed by baloo" in read(local)
                self.assertEqual(kept, yml != "status-line: false\n")

    # In a Session review's session, session start changes nothing in the repo or Claude Code's
    # settings, and only names the Guidelines.
    def test_in_session_review(self):
        dir = in_repo(self)
        os.environ[review.ENV] = "1"
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), ENABLE)
        self.assertEqual(start(self), (0, "", ""))
        self.assertFalse(os.path.exists(os.path.join(dir, names.CONFIG)))
        write(
            os.path.join(dir, names.CONFIG),
            "output-style: short-replies\nstatus-line: true\nguidelines:\n  go: true\n"
            "git-hooks:\n  no-secrets-in-commits: true\n",
        )
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith(
            "Read a file when its task comes up:\n- Writing Go: "
            + os.path.join(PLUGIN, "guidelines", "go.md") + "\n"
        ), out)
        self.assertNotIn("baloo:", out)
        for path in [names.LOCAL_SETTINGS, ".git/hooks/pre-commit"]:
            self.assertFalse(os.path.exists(os.path.join(dir, path)), path)
        self.assertFalse(
            os.path.lexists(os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN))
        )

    # Session start says how many items the Inbox holds, one per `## ` heading outside a code
    # block, and nothing of an empty one.
    def test_inbox(self):
        dir = in_repo(self)
        path = os.path.join(dir, names.INBOX)
        tail = ": tell the user, and that /baloo:inbox goes through them\n"
        for inbox, want in [
            ("# Inbox\n\n## One\n\ntext\n### not an item\n\n## Two\n",
             ".about/inbox.md holds 2 items to consider" + tail),
            ("# Inbox\n\n## One\n\n```md\n## not an item\n```\n",
             ".about/inbox.md holds 1 item to consider" + tail),
            ("# Inbox\n", ""),
            ("# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n\n## Two\n\n2026-10-01 · adr"
             "\n\ntext · kept 2026-10-02\n",
             ".about/inbox.md holds 2 items to consider, 1 not gone through yet" + tail),
            ("# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n",
             ".about/inbox.md holds 1 item to consider, each gone through once and kept" + tail),
        ]:
            with self.subTest(inbox=inbox):
                write(path, inbox)
                code, out, _ = start(self)
                self.assertEqual(code, 0)
                if want:
                    self.assertIn("\n" + want, out)
                else:
                    self.assertNotIn(names.INBOX + " holds", out)

    # Session start names a Check a Hook runs that the Config turns off, for the user.
    def test_checks_off(self):
        dir = in_repo(self)
        write(os.path.join(dir, names.CONFIG), "claude-hooks:\n  no-secrets-in-context: false\n")
        code, out, _ = start(self)
        self.assertEqual((code, out), (0, (
            "baloo:\nclaude-hooks.no-secrets-in-context: false in .claude/baloo.yml turns off a "
            "check in Claude Code's hooks: tell the user\n"
        )))

    # Outside a repo, such as in the home folder, session start writes nothing and says nothing.
    def test_outside_repo(self):
        commands.env(self)
        dir = commands.outside_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = dir
        self.assertEqual(start(self), (0, "", ""))
        self.assertEqual(os.listdir(dir), [])

    # Session start names each Guideline the Config turns on, after the rules for every task, and
    # none that is off.
    def test_guidelines(self):
        dir = in_repo(self)
        os.environ["SHELL"] = "/bin/bash"
        config = os.path.join(dir, names.CONFIG)
        write(config, "guidelines:\n  principles: true\n  go: true\n  vue: false\n")
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("In zsh:", out)
        folder = os.path.join(PLUGIN, "guidelines")
        for want in [
            "On every task:\nFor a trivial change",
            "- Done is verifiable: say how someone else can check it without asking you.\n",
            "- Writing Go: " + os.path.join(folder, "go.md") + "\n",
            "change): " + os.path.join(folder, "principles.md") + "\n",
        ]:
            self.assertIn(want, out)
        for unwanted in ["vue.md", "design.md", "\n## "]:
            self.assertNotIn(unwanted, out)
        # Where the Bash tool runs zsh, the rules zsh needs follow them.
        os.environ["CLAUDE_CODE_SHELL"] = "/usr/bin/zsh"
        self.assertIn("In zsh:\n- ", start(self)[1])
        # Without principles, the rules for every task aren't printed.
        write(config, "guidelines:\n  go: true\n")
        out = start(self)[1]
        self.assertNotIn("On every task", out)
        self.assertIn("go.md", out)
        # Without the plugin's folder, no Guideline can be named: one problem.
        os.environ["CLAUDE_PLUGIN_ROOT"] = ""
        self.assertEqual(
            start(self)[1], "baloo:\ncould not name the guidelines: CLAUDE_PLUGIN_ROOT is not set\n"
        )

    # A setting an earlier Release had, such as stop-check, is not reported at session start: the
    # Config works as without it, and doctor names it (ADR measurement).
    def test_ignores_removed_settings(self):
        dir = in_repo(self)
        write(
            os.path.join(dir, names.CONFIG),
            "stop-check: make\nclaude-hooks:\n  no-destructive-commands: true\n",
        )
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertNotIn("stop-check", out)
        self.assertNotIn("no-destructive-commands", out)

    # Session start points the link in the plugin's data folder at this version's plugin, which
    # tells a later prompt that it ran.
    def test_points_the_link(self):
        in_repo(self)
        start(self)
        link = os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN)
        self.assertEqual(os.path.realpath(link), PLUGIN)


class PromptAfterUpdate(unittest.TestCase):
    # In a session the plugin was updated in, the first prompt runs this version's session start,
    # which no SessionStart Hook ran for; once it has run, a prompt runs none.
    def test_runs_session_start_once(self):
        dir = in_repo(self)
        data = os.environ["CLAUDE_PLUGIN_DATA"]
        old = commands.testkit.tempdir(self)
        os.symlink(old, os.path.join(data, names.PLUGIN))  # the version before's
        code, out, err = run("user-prompt-submit", stdin='{"session_id":"s1"}')
        self.assertEqual((code, err), (0, ""))
        hook = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hook["hookEventName"], "UserPromptSubmit")
        self.assertIn("created " + os.path.join(dir, names.CONFIG), hook["additionalContext"])
        self.assertEqual(os.path.realpath(os.path.join(data, names.PLUGIN)), PLUGIN)
        self.assertEqual(run("user-prompt-submit", stdin='{"session_id":"s1"}'), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
