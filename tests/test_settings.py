import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from baloo import names, settings


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


class TempDir(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = os.path.realpath(tmp.name)


class Set(unittest.TestCase):
    def test_set(self):
        field = '"outputStyle": "x"'
        fresh = "{\n  " + field + "\n}\n"
        for data, want in [
            ("", fresh),
            (" \n", fresh),
            ("{}", fresh),
            ("{ }", fresh),
            ("{\n}\n", fresh),
            ("null", fresh),
            ('{\n  "a": 1\n}\n', "{\n  " + field + ',\n  "a": 1\n}\n'),
            # A field that is there is set in place.
            ('{\n  "a": 1,\n  "outputStyle": {"b": [2]}\n}\n', '{\n  "a": 1,\n  ' + field + "\n}\n"),
            ('{"outputStyle":null,"a":1}', '{"outputStyle":"x","a":1}'),
            # Only a top-level field counts.
            ('{"a": {"outputStyle": 1}}', "{\n  " + field + ',"a": {"outputStyle": 1}}'),
        ]:
            with self.subTest(data=data):
                self.assertEqual(settings._set(data, "outputStyle", '"x"'), want)

    def test_not_an_object(self):
        for data in ["[]", "{nope", "1", '{"a": 1} {']:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    settings._set(data, "outputStyle", '"x"')


class Delete(TempDir):
    # A field is taken out with its comma, and the rest of the file stays as it was.
    def test_delete(self):
        for data, want in [
            ('{\n  "s": {"c": 1},\n  "a": 1\n}\n', '{\n  "a": 1\n}\n'),
            ('{\n  "a": 1,\n  "s": {"c": 1}\n}\n', '{\n  "a": 1\n}\n'),
            ('{\n  "a": 1,\n  "s": 2,\n  "b": 3\n}\n', '{\n  "a": 1,\n  "b": 3\n}\n'),
            ('{"s":2,"a":1}', '{"a":1}'),
            ('{\n  "s": 2\n}\n', "{\n}\n"),
            ('{\n  "a": {"s": 1}\n}\n', '{\n  "a": {"s": 1}\n}\n'),
        ]:
            with self.subTest(data=data):
                path = os.path.join(self.dir, "settings.json")
                write(path, data)
                settings.delete(path, "s")
                self.assertEqual(contents(path), want)


class Replace(TempDir):
    # A settings file is replaced whole, through a link to it too, and keeps its mode.
    def test_replace(self):
        real = os.path.join(self.dir, "real.json")
        write(real, "{}")
        os.chmod(real, 0o600)
        link = os.path.join(self.dir, "link.json")
        os.symlink(real, link)
        settings._replace(link, '{"a": 1}')
        self.assertEqual(contents(real), '{"a": 1}')
        self.assertTrue(os.path.islink(link))
        self.assertEqual(stat.S_IMODE(os.stat(real).st_mode), 0o600)
        self.assertEqual(len(os.listdir(self.dir)), 2)


class Pattern(unittest.TestCase):
    def test_pattern(self):
        for rel, want in {
            "a/.claude/settings.local.json": "a/.claude/settings.local.json",
            "a[1]/b*/c?/d\\e": "a\\[1]/b\\*/c\\?/d\\\\e",
            "a /x": "a /x",
            "#a/!b": "#a/!b",
            "trailing  ": "trailing\\ \\ ",
        }.items():
            with self.subTest(rel=rel):
                self.assertEqual(settings._pattern(rel), want)


class Exclude(TempDir):
    # A file goes into info/exclude once, and a worktree's goes into the one its worktrees share.
    def test_exclude(self):
        path = os.path.join(self.dir, names.LOCAL_SETTINGS)
        write(os.path.join(self.dir, ".git", "info", "exclude"), "# git's own")
        settings.exclude(self.dir, path)
        settings.exclude(self.dir, path)
        self.assertEqual(
            contents(os.path.join(self.dir, ".git", "info", "exclude")),
            "# git's own\n/.claude/settings.local.json\n",
        )

    def test_worktree(self):
        main = os.path.join(self.dir, "main")
        tree = os.path.join(self.dir, "tree")
        write(os.path.join(main, ".git", "worktrees", "tree", "commondir"), "../..\n")
        write(os.path.join(tree, ".git"), "gitdir: ../main/.git/worktrees/tree\n")
        settings.exclude(tree, os.path.join(tree, names.LOCAL_SETTINGS))
        self.assertEqual(
            contents(os.path.join(main, ".git", "info", "exclude")),
            "/.claude/settings.local.json\n",
        )


class SetUnset(TempDir):
    def setUp(self):
        super().setUp()
        own = os.path.join(self.dir, "own")
        env = {"CLAUDE_CONFIG_DIR": own, "BALOO_MANAGED_SETTINGS": os.path.join(self.dir, "none")}
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)
        self.user = os.path.join(own, "settings.json")
        self.project = os.path.join(self.dir, "repo")
        os.makedirs(os.path.join(self.project, ".git"))

    def on(self, path):
        write(path, json.dumps({"enabledPlugins": {names.PLUGIN_ID: True}}))

    # Enabled for the user, the field goes into the project's settings.local.json, excluded.
    def test_user_scope(self):
        self.on(self.user)
        path, scope, err = settings.set_unset(self.project, self.project, ["k"], "k", {"a": 1})
        local = os.path.join(self.project, names.LOCAL_SETTINGS)
        self.assertEqual((path, scope, err), (local, settings.USER, None))
        self.assertEqual(json.loads(contents(local)), {"k": {"a": 1}})
        exclude = contents(os.path.join(self.project, ".git", "info", "exclude"))
        self.assertEqual(exclude, "/.claude/settings.local.json\n")

    # Enabled for the team, the field goes into the team's settings.json.
    def test_project_scope(self):
        team = os.path.join(self.project, names.PROJECT_SETTINGS)
        self.on(team)
        path, scope, _ = settings.set_unset(self.project, self.project, ["k"], "k", "v")
        self.assertEqual((path, scope), (team, settings.PROJECT))
        self.assertEqual(json.loads(contents(team))["k"], "v")

    # A key set in any settings file, or the plugin not enabled, writes nothing.
    def test_nothing_written(self):
        write(self.user, json.dumps({"enabledPlugins": {names.PLUGIN_ID: True}, "other": 1}))
        got = settings.set_unset(self.project, self.project, ["k", "other"], "k", "v")
        self.assertEqual(got, ("", "", None))
        write(self.user, json.dumps({"enabledPlugins": {names.PLUGIN_ID: False}}))
        self.assertEqual(settings.set_unset(self.project, self.project, ["k"], "k", "v"), ("", "", None))
        self.assertFalse(os.path.exists(os.path.join(self.project, names.LOCAL_SETTINGS)))

    # The most specific settings file that names the plugin decides; managed settings don't count.
    def test_enabling(self):
        on = {"enabledPlugins": {names.PLUGIN_ID: True}}
        off = {"enabledPlugins": {names.PLUGIN_ID: False}}
        for fields, want in [
            ({settings.USER: on}, settings.USER),
            ({settings.LOCAL: off, settings.USER: on}, ""),
            ({settings.PROJECT: on, settings.USER: off}, settings.PROJECT),
            ({settings.MANAGED: on}, ""),
            ({settings.LOCAL: {"enabledPlugins": []}, settings.USER: on}, settings.USER),
        ]:
            with self.subTest(fields=fields):
                self.assertEqual(settings.enabling(fields), want)

    def test_broken_file(self):
        write(self.user, "{nope")
        path, scope, err = settings.set_unset(self.project, self.project, ["k"], "k", "v")
        self.assertEqual((path, scope), ("", ""))
        self.assertTrue(str(err).startswith(self.user + ": "), err)


if __name__ == "__main__":
    unittest.main()
