import json
import os
import unittest

from louie import names
from tests.louie import commands
from tests.louie.commands import PLUGIN, in_repo, read, run, start, write

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

    # Session start creates no Config and writes no file under the repo, .git/ included, and an
    # old Config changes nothing it says (PRD no-config).
    def test_writes_nothing(self):
        dir = in_repo(self)

        def tree():
            got = {}
            for folder, _, files in os.walk(dir):
                for name in files:
                    path = os.path.join(folder, name)
                    with open(path, "rb") as f:
                        got[path] = f.read()
            return got

        before = tree()
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(tree(), before)
        self.assertFalse(os.path.exists(os.path.join(dir, ".claude/baloo.yml")))
        write(os.path.join(dir, ".claude/baloo.yml"), "nope: 1\nformat-on-edit: x\n")
        self.assertNotIn("baloo.yml", start(self)[1])

    # Session start writes no Git hook, leaves Claude Code's commit attribution to the project's
    # settings and the commit format to CLAUDE.md, and says nothing of either, whatever an old
    # Config says (ADR git-hooks).
    def test_leaves_commits_alone(self):
        dir = in_repo(self)
        settings = os.path.join(dir, names.PROJECT_SETTINGS)
        write(settings, ENABLE)
        write(os.path.join(dir, ".claude/baloo.yml"),
              "git-hooks:\n  conventional-commits: true\n  no-ai-coauthor: true\n")
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        for word in ["attribution", "commit message", "Git hook"]:
            self.assertNotIn(word, out)
        self.assertNotIn("attribution", read(settings))
        hooks = os.path.join(dir, ".git", "hooks")
        self.assertEqual([f for f in os.listdir(hooks) if not f.endswith(".sample")], [])

    # In a Session review's session, session start changes nothing in the repo or Claude Code's
    # settings, and only names the Guidelines.
    def test_in_session_review(self):
        dir = in_repo(self)
        os.environ["BALOO_SESSION_REVIEW"] = "1"
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), ENABLE)
        write(os.path.join(dir, "go.mod"), "module x\n")
        write(os.path.join(dir, ".claude/baloo.yml"), "output-style: short-replies\nstatus-line: true\n")
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Guidelines, "), out)
        self.assertTrue(
            out.endswith("- Writing Go: " + os.path.join(PLUGIN, "guidelines", "go.md") + "\n"), out
        )
        self.assertFalse(out.startswith("louie:"), out)
        for path in [names.LOCAL_SETTINGS, ".git/hooks/pre-commit"]:
            self.assertFalse(os.path.exists(os.path.join(dir, path)), path)
        self.assertFalse(
            os.path.lexists(os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN))
        )

    # An old Config that turns a Check off is said nothing of: the Check runs (PRD no-config).
    def test_checks_off(self):
        dir = in_repo(self)
        write(os.path.join(dir, ".claude/baloo.yml"), "claude-hooks:\n  no-secrets-in-context: false\n")
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertNotIn("claude-hooks", out)

    # Outside a repo, such as in the home folder, session start writes nothing and says nothing.
    def test_outside_repo(self):
        commands.env(self)
        dir = commands.outside_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = dir
        self.assertEqual(start(self), (0, "", ""))
        self.assertEqual(os.listdir(dir), [])

    # Session start names each Guideline no Hook gives that fits the repo, after the rules for
    # every task, whatever an old Config turns off (PRD no-config).
    def test_guidelines(self):
        dir = in_repo(self)
        os.environ["SHELL"] = "/bin/bash"
        write(os.path.join(dir, "go.mod"), "module x\n")
        write(os.path.join(dir, ".claude/baloo.yml"), "guidelines:\n  go: false\n  principles: false\n")
        code, out, err = start(self)
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("In zsh:", out)
        folder = os.path.join(PLUGIN, "guidelines")
        for want in [
            "On every task:\nFor a trivial change",
            "- Done is verifiable: say how someone else can check it without asking you.\n",
            "- Writing Go: " + os.path.join(folder, "go.md") + "\n",
            "change): " + os.path.join(folder, "principles.md") + "\n",
            "tested from: " + os.path.join(folder, "design.md") + "\n",
        ]:
            self.assertIn(want, out)
        for unwanted in ["vue.md", "tailwind.md", "\n## "]:
            self.assertNotIn(unwanted, out)
        # Where the Bash tool runs zsh, the rules zsh needs follow them.
        os.environ["CLAUDE_CODE_SHELL"] = "/usr/bin/zsh"
        self.assertIn("In zsh:\n- ", start(self)[1])
        # Without the plugin's folder, no Guideline can be named: one problem.
        os.environ["CLAUDE_PLUGIN_ROOT"] = ""
        self.assertEqual(
            start(self)[1], "louie:\ncould not name the guidelines: CLAUDE_PLUGIN_ROOT is not set\n"
        )

    # A setting an earlier Release had, such as stop-check, is not reported at session start: the
    # Config works as without it, and doctor names it (ADR measurement).
    def test_ignores_removed_settings(self):
        dir = in_repo(self)
        write(
            os.path.join(dir, ".claude/baloo.yml"),
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
        in_repo(self)
        data = os.environ["CLAUDE_PLUGIN_DATA"]
        old = commands.testkit.tempdir(self)
        os.symlink(old, os.path.join(data, names.PLUGIN))  # the version before's
        code, out, err = run("user-prompt-submit", stdin='{"session_id":"s1"}')
        self.assertEqual((code, err), (0, ""))
        hook = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hook["hookEventName"], "UserPromptSubmit")
        self.assertIn("Guidelines, the plugin's working rules", hook["additionalContext"])
        self.assertEqual(os.path.realpath(os.path.join(data, names.PLUGIN)), PLUGIN)
        self.assertEqual(run("user-prompt-submit", stdin='{"session_id":"s1"}'), (0, "", ""))

    # What session start tells and what the prompt tells reach Claude in one JSON: Claude Code
    # drops a Hook's output that holds two.
    def test_tells_in_one_answer(self):
        dir = in_repo(self)
        data = os.environ["CLAUDE_PLUGIN_DATA"]
        os.symlink(commands.testkit.tempdir(self), os.path.join(data, names.PLUGIN))
        write(
            os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "plugins", "installed_plugins.json"),
            json.dumps({"plugins": {names.PLUGIN_ID: [
                {"scope": "local", "projectPath": dir, "version": "99.0.0"}
            ]}}),
        )
        code, out, err = run("user-prompt-submit", stdin='{"session_id":"s1"}')
        self.assertEqual((code, err), (0, ""))
        told = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Guidelines, the plugin's working rules", told)
        self.assertIn("but 99.0.0 is installed for this project", told)


if __name__ == "__main__":
    unittest.main()
