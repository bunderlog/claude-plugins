import json
import os
import tempfile
import unittest
from unittest import mock

from baloo import names, outputstyle, settings

ON = '{"enabledPlugins": {"' + names.PLUGIN_ID + '": true}}'
OFF = '{"enabledPlugins": {"' + names.PLUGIN_ID + '": false}}'


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def contents(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


class Sandbox(unittest.TestCase):
    def sandbox(self):
        """A temporary repo with the user's and the managed settings of its own, none of them
        there yet; its root and Claude Code's own folder."""
        root, own = self.tempdir(), self.tempdir()
        os.mkdir(os.path.join(root, ".git"))
        env = mock.patch.dict(
            os.environ,
            {
                "CLAUDE_CONFIG_DIR": own,
                "BALOO_MANAGED_SETTINGS": os.path.join(own, "managed-settings.json"),
            },
        )
        env.start()
        self.addCleanup(env.stop)
        return root, own

    def tempdir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return os.path.realpath(tmp.name)


class Pick(Sandbox):
    def test_pick(self):
        local, project = names.LOCAL_SETTINGS, names.PROJECT_SETTINGS
        on_in_project = (
            '{"outputStyle": "x", "enabledPlugins": {"' + names.PLUGIN_ID + '": true}}'
        )
        # local, project, user, managed, and where it writes, or "" for nowhere.
        for name, here, team, user, managed, where in [
            ("enabled in the project", "", ON, "", "", project),
            ("enabled in the project, an empty file here", " \n", ON, "", "", project),
            ("enabled here", ON, "", "", "", local),
            ("enabled for the user", "", "", ON, "", local),
            ("enabled here and in the project", ON, ON, "", "", local),
            ("enabled in the project and for the user", "", ON, ON, "", project),
            ("not enabled anywhere", "", "", "", "", ""),
            ("enabled only by managed settings", "", "", "", ON, ""),
            ("another plugin enabled", "", '{"enabledPlugins": {"x@y": true}}', "", "", ""),
            ("turned off here, on for the user", OFF, "", ON, "", ""),
            ("turned off in the project, on for the user", "", OFF, ON, "", ""),
            ("turned on here, off in the project", ON, OFF, "", "", local),
            ("a style set here", '{"outputStyle": "Explanatory"}', ON, "", "", ""),
            ("a style set in the project", "", on_in_project, "", "", ""),
            ("the default style set for the user", "", ON, '{"outputStyle": "default"}', "", ""),
            ("a style set by managed settings", "", ON, "", '{"outputStyle": "x"}', ""),
        ]:
            with self.subTest(name):
                root, own = self.sandbox()
                for path, text in [
                    (os.path.join(root, local), here),
                    (os.path.join(root, project), team),
                    (os.path.join(own, "settings.json"), user),
                    (os.path.join(own, "managed-settings.json"), managed),
                ]:
                    if text:
                        write(path, text)
                got, err = outputstyle.pick(root, root, "short-replies")
                self.assertIsNone(err)
                self.assertEqual(got.path, os.path.join(root, where) if where else "")
                for file in (local, project):
                    text = contents(os.path.join(root, file))
                    fields = json.loads(text) if text.strip() else {}
                    written = fields.get("outputStyle") == "baloo:short-replies"
                    self.assertEqual(written, file == where, file)

    # A settings file that was there keeps the rest of its text as it was.
    def test_keeps_the_file(self):
        root, _ = self.sandbox()
        local = os.path.join(root, names.LOCAL_SETTINGS)
        text = '{\n  "enabledPlugins": {\n    "' + names.PLUGIN_ID + '": true\n  }\n}\n'
        write(local, text)
        _, err = outputstyle.pick(root, root, "short-replies")
        self.assertIsNone(err)
        self.assertEqual(
            contents(local),
            '{\n  "outputStyle": "baloo:short-replies",\n'
            '  "enabledPlugins": {\n    "baloo@bunderlog": true\n  }\n}\n',
        )
        self.assertEqual(contents(os.path.join(root, ".git", "info", "exclude")), "")

    # With the plugin enabled for the user, the settings.local.json it creates goes into
    # info/exclude once, even for a worktree, whose info/ is the one its repo's worktrees share.
    def test_excludes(self):
        root, own = self.sandbox()
        write(os.path.join(own, "settings.json"), ON)
        exclude = os.path.join(root, ".git", "info", "exclude")
        write(exclude, "# git's own comment")
        for _ in range(2):
            try:
                os.remove(os.path.join(root, names.LOCAL_SETTINGS))
            except FileNotFoundError:
                pass
            _, err = outputstyle.pick(root, root, "short-replies")
            self.assertIsNone(err)
        self.assertEqual(
            contents(exclude), "# git's own comment\n/.claude/settings.local.json\n"
        )

        main, own = self.sandbox()
        write(os.path.join(own, "settings.json"), ON)
        tree = self.tempdir()
        gitdir = os.path.join(main, ".git", "worktrees", "tree")
        write(os.path.join(gitdir, "commondir"), "../..\n")
        write(os.path.join(tree, ".git"), "gitdir: " + gitdir + "\n")
        _, err = outputstyle.pick(tree, tree, "short-replies")
        self.assertIsNone(err)
        self.assertEqual(
            contents(os.path.join(main, ".git", "info", "exclude")),
            "/.claude/settings.local.json\n",
        )

    # A settings file that isn't JSON is a problem, and nothing is written.
    def test_bad_settings(self):
        root, _ = self.sandbox()
        project = os.path.join(root, names.PROJECT_SETTINGS)
        write(project, "{nope")
        got, err = outputstyle.pick(root, root, "short-replies")
        self.assertEqual(got.path, "")
        self.assertIn(project, str(err))
        local = os.path.join(root, names.LOCAL_SETTINGS)
        write(project, ON)
        write(local, "[]")
        got, err = outputstyle.pick(root, root, "short-replies")
        self.assertEqual(got.path, "")
        self.assertIsNotNone(err)
        self.assertEqual(contents(local), "[]")

    # Picked names the Scope that enables the plugin, which may not be the file's.
    def test_scope(self):
        for scope, file in [
            (settings.LOCAL, names.LOCAL_SETTINGS),
            (settings.PROJECT, names.PROJECT_SETTINGS),
            (settings.USER, ""),
        ]:
            with self.subTest(scope):
                root, own = self.sandbox()
                write(os.path.join(root, file) if file else os.path.join(own, "settings.json"), ON)
                got, err = outputstyle.pick(root, root, "short-replies")
                self.assertIsNone(err)
                self.assertEqual(got.enabled, scope)


if __name__ == "__main__":
    unittest.main()
