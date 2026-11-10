import json
import os
import unittest

from bagheera import names
from tests.bagheera import commands
from tests.bagheera.commands import PLUGIN, in_repo, run, start, write

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
        self.assertFalse(os.path.exists(os.path.join(dir, names.OLD_CONFIG)))
        write(os.path.join(dir, names.OLD_CONFIG), "nope: 1\nformat-on-edit: x\n")
        self.assertNotIn("baloo.yml", start(self)[1])

    # Where no settings file sets an Output style or a Status line, session start tells, once per
    # clone, how the person sets each in their own settings, and writes neither; a headless session
    # doesn't use the telling up, and one already set isn't told of (PRD no-config).
    def test_personal(self):
        dir = in_repo(self)
        user = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json")
        write(user, ENABLE)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertNotIn("no longer picks", start(self)[1])
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        out = start(self)[1]
        self.assertIn("bagheera no longer picks an Output style or sets a Status line", out)
        self.assertIn('"outputStyle": "bagheera:short-replies"', out)
        self.assertIn('"statusLine": {"type": "command"', out)
        self.assertFalse(os.path.exists(os.path.join(dir, names.LOCAL_SETTINGS)))
        self.assertNotIn("no longer picks", start(self)[1])

        dir = in_repo(self)
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"),
              '{"outputStyle": "Explanatory", "statusLine": {"type": "command", "command": "x"}}')
        self.assertNotIn("no longer picks", start(self)[1])

    # In a Session review's session, session start says nothing and changes nothing in the repo
    # or Claude Code's settings.
    def test_in_session_review(self):
        dir = in_repo(self)
        os.environ["BALOO_SESSION_REVIEW"] = "1"
        write(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), ENABLE)
        code, out, _ = start(self)
        self.assertEqual((code, out), (0, ""))
        for path in [names.LOCAL_SETTINGS, ".git/hooks/pre-commit"]:
            self.assertFalse(os.path.exists(os.path.join(dir, path)), path)
        self.assertFalse(
            os.path.lexists(os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], names.PLUGIN))
        )

    # Outside a repo, such as in the home folder, session start writes nothing and says nothing.
    def test_outside_repo(self):
        commands.env(self)
        dir = commands.outside_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = dir
        self.assertEqual(start(self), (0, "", ""))
        self.assertEqual(os.listdir(dir), [])

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
        self.assertIn("no longer picks an Output style", hook["additionalContext"])
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
        self.assertIn("no longer picks an Output style", told)
        self.assertIn("but 99.0.0 is installed for this project", told)


if __name__ == "__main__":
    unittest.main()
