import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from baloo import checks, config, guidelines, names
from baloo.config import parse

ROOT = os.path.dirname(os.path.dirname(__file__))
PLUGIN = os.path.join(ROOT, names.PLUGIN_DIR)


def schema():
    with open(os.path.join(PLUGIN, "schema.json"), encoding="utf-8") as f:
        return json.load(f)


class Case(unittest.TestCase):
    def tempdir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def temp_repo(self):
        """A temporary git repo, as far as config can tell, with a folder inside it."""
        root = self.tempdir()
        sub = os.path.join(root, "a", "b")
        os.makedirs(os.path.join(root, ".git"))
        os.makedirs(sub)
        return root, sub

    def outside_repo(self):
        """A temporary folder in no repo; the test is skipped when the temporary folders are
        inside one themselves, since every walk up would reach that repo."""
        d = self.tempdir()
        if config._repo(d)[1]:
            self.skipTest("the temporary folders are inside a repo")
        return d

    def write_config(self, root, text):
        os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
        with open(os.path.join(root, names.CONFIG), "w", encoding="utf-8") as f:
            f.write(text)

    def setenv(self, key, value):
        patch = mock.patch.dict(os.environ, {key: value})
        patch.start()
        self.addCleanup(patch.stop)


class Repo(Case):
    def test_finds_the_root_from_a_folder_inside(self):
        root, sub = self.temp_repo()
        self.assertEqual(config._repo(sub), (root, True))

    def test_a_worktree_is_its_own_root(self):
        _, sub = self.temp_repo()
        inner = os.path.join(sub, "worktree")
        os.makedirs(inner)
        with open(os.path.join(inner, ".git"), "w") as f:
            f.write("gitdir: elsewhere\n")
        self.assertEqual(config._repo(inner), (inner, True))

    def test_outside_a_repo(self):
        outside = self.outside_repo()
        self.assertEqual(config._repo(outside), (outside, False))


class Load(Case):
    def test_creates_the_template_and_never_writes_one_there(self):
        root, sub = self.temp_repo()
        _, created, problems = config.load(sub)
        self.assertEqual((created, problems), (os.path.join(root, names.CONFIG), []))
        with open(created, encoding="utf-8") as f:
            self.assertEqual(f.read(), config._new_config())
        with open(created, "w") as f:
            f.write("nope: 1\n")
        _, again, problems = config.load(root)
        self.assertEqual((again, len(problems)), ("", 1))
        with open(created) as f:
            self.assertEqual(f.read(), "nope: 1\n")

    def test_the_home_folder_and_claude_codes_own(self):
        # The home folder as a repo, a dotfiles one, with a folder in it that isn't a repo of its
        # own.
        home, in_home = self.temp_repo()
        self.setenv("HOME", home)
        self.assertEqual(config.load(in_home)[1:], ("", []))
        self.assertFalse(os.path.exists(os.path.join(home, ".claude")))
        # Its .claude/ is Claude Code's own, so a baloo.yml there is not read either.
        self.write_config(home, "nope: 1\n")
        self.assertEqual(config.load(in_home)[2], [])
        # The same, reached through a link to the home folder.
        link = os.path.join(self.tempdir(), "home")
        os.symlink(home, link)
        self.setenv("HOME", link)
        self.assertEqual(config.load(in_home)[1:], ("", []))
        # Claude Code's own folder as a repo, and a repo inside it, such as a marketplace it cloned.
        self.setenv("CLAUDE_CONFIG_DIR", "")
        own = os.path.join(home, ".claude")
        for root in [own, os.path.join(own, "plugins", "marketplaces", "m")]:
            os.makedirs(os.path.join(root, ".git"))
            self.assertEqual(config.load(root)[1], "", root)
        # The same folder moved by CLAUDE_CONFIG_DIR, while ~/.claude is no longer Claude Code's.
        moved, in_moved = self.temp_repo()
        self.setenv("CLAUDE_CONFIG_DIR", moved)
        self.assertEqual(config.load(in_moved)[1], "")
        self.assertNotEqual(config.load(own)[1], "")

    def test_outside_a_repo(self):
        outside = self.outside_repo()
        self.assertEqual(config.load(outside)[1:], ("", []))
        self.assertEqual(os.listdir(outside), [])
        self.write_config(outside, "nope: 1\n")
        self.assertEqual(config.load(outside)[2], [])

    # Load reads the Config at the repo's root from any folder inside it, and a Config it can't
    # read, or can't create, is one problem.
    def test_problems(self):
        root, sub = self.temp_repo()
        self.write_config(root, "nope: 1\n")
        problems = config.load(sub)[2]
        self.assertEqual(len(problems), 1)
        self.assertIn("nope is not a setting", problems[0])
        if os.getuid() == 0:
            self.skipTest("root reads and writes whatever the permissions say")
        path = os.path.join(root, names.CONFIG)
        os.chmod(path, 0)
        problems = config.load(sub)[2]
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].endswith("none of it applies"), problems)
        os.remove(path)
        claude = os.path.join(root, ".claude")
        os.chmod(claude, 0o555)
        self.addCleanup(os.chmod, claude, 0o755)
        _, created, problems = config.load(sub)
        self.assertEqual((created, problems), ("", [f"could not create {path}: permission denied"]))


class Read(Case):
    # Read reads a Config as Load does, but never creates one.
    def test_never_creates(self):
        root, sub = self.temp_repo()
        c = config.read(sub)
        self.assertEqual(c.root, root)
        self.assertTrue(c.check_on("no-secrets-in-context"))
        self.assertFalse(os.path.exists(os.path.join(root, names.CONFIG)))
        self.write_config(root, "claude-hooks:\n  no-secrets-in-context: false\n")
        self.assertTrue(config.read(sub).check_on("no-secrets-in-context"))

    def test_inspect(self):
        root, sub = self.temp_repo()
        self.assertEqual(config.inspect(sub)[1:], ("", []))
        self.write_config(root, "nope: 1\n")
        c, path, problems = config.inspect(sub)
        self.assertEqual((c.root, path), (root, os.path.join(root, names.CONFIG)))
        self.assertEqual(problems, [".claude/baloo.yml line 1: nope is not a setting; ignored"])


class Parse(Case):
    def test_the_file(self):
        for name, yml, problems in [
            ("a new config", config._new_config(), []),
            ("an empty file", "", []),
            ("only comments", "# nothing yet\n", []),
            ("an empty map", "{}\n", []),
            ("keys that aren't settings", "# a comment\nnope: true\nalso: [1]\n", [
                ".claude/baloo.yml line 2: nope is not a setting; ignored",
                ".claude/baloo.yml line 3: also is not a setting; ignored",
            ]),
            ("a list", "- a\n- b\n", [
                ".claude/baloo.yml line 1: not a map of settings; none of it applies",
            ]),
            ("a scalar", "true\n", [
                ".claude/baloo.yml line 1: not a map of settings; none of it applies",
            ]),
            ("not YAML", "a: [1\n", [
                ".claude/baloo.yml: line 1: did not find expected ',' or ']'; none of it applies",
            ]),
        ]:
            with self.subTest(name):
                self.assertEqual(parse(yml)[1], problems)

    # A setting whose value doesn't decode is a problem, and the settings around it still apply.
    def test_a_wrong_setting_leaves_the_others(self):
        got = []

        def probe(c, key, value):
            if value.tag != "bool":
                return [config._wrong(key.line, key.text, "is not true or false")]
            got.append(value.text)
            return []

        with mock.patch.dict(config._KEYS, {"probe": probe, "probe-2": probe}):
            _, problems = parse("probe: true\nnope: 1\nprobe-2: maybe\n")
        self.assertEqual(problems, [
            ".claude/baloo.yml line 2: nope is not a setting; ignored",
            ".claude/baloo.yml line 3: probe-2: is not true or false; its default applies",
        ])
        self.assertEqual(got, ["true"])

class Settings(Case):
    # The Session review is on with its key, off without it, and on in a new Config (ADR
    # session-review).
    def test_session_review(self):
        for yml, on, problems in [
            ("session-review: true\n", True, []),
            ("session-review: false\n", False, []),
            ("# none\n", False, []),
            ("session-review: yes please\n", False, [
                ".claude/baloo.yml line 1: session-review: is not true or false; its default"
                " applies",
            ]),
            (config._new_config(), True, []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.session_review, got), (on, problems))

    # A setting an earlier Release had is no problem: the Config works as without it, the settings
    # beside it apply, and doctor gets a line naming it to delete (ADR measurement).
    def test_removed(self):
        yml = (
            "stop-check: mise run check\nclaude-hooks:\n  no-destructive-commands: true\n"
            "  no-secrets-in-context: false\nformat-on-edit: npx prettier --write\n"
            "git-hooks:\n  no-ai-coauthor: true\ngit-hook-commands:\n  pre-commit: mise run test\n"
        )
        c, problems = parse(yml)
        self.assertEqual(problems, [])
        self.assertEqual(c.removed, [
            ".claude/baloo.yml line 1: stop-check is no longer a setting and is ignored: delete it",
            ".claude/baloo.yml line 2: claude-hooks is no longer a setting and is ignored: delete"
            " it",
            ".claude/baloo.yml line 6: git-hooks is no longer a setting and is ignored: delete it",
            ".claude/baloo.yml line 8: git-hook-commands is no longer a setting and is ignored:"
            " delete it",
        ])
        self.assertTrue(c.check_on("no-secrets-in-context"))
        self.assertEqual(c.format_on_edit, "npx prettier --write")
        self.assertNotIn("stop-check", config._new_config())
        self.assertNotIn("no-destructive-commands", config._new_config())
        self.assertNotIn("git-hooks:", config._new_config())
        self.assertNotIn("git-hook-commands", config._new_config())
        self.assertNotIn("claude-hooks", config._new_config())
        self.assertNotIn("guidelines:", config._new_config())

    # format-on-edit names the command run on each file Claude edits; without it, or false, it is
    # off, and a new Config has it only as a comment (ADR format-on-edit).
    def test_format_on_edit(self):
        for yml, command, problems in [
            ("format-on-edit: npx prettier --write\n", "npx prettier --write", []),
            ("format-on-edit: false\n", "", []),
            ("format-on-edit: [prettier]\n", "", [
                ".claude/baloo.yml line 1: format-on-edit: is not a command or false; its default"
                " applies",
            ]),
            (config._new_config(), "", []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.format_on_edit, got), (command, problems))
        self.assertIn("\n# format-on-edit: npx prettier --write\n", config._new_config())

    # Each Check a Hook runs is always on, whatever an old Config says (PRD no-config).
    def test_checks(self):
        for yml in ["", "claude-hooks:\n  no-secrets-in-context: false\n  no-git-hook-bypass: false\n"]:
            with self.subTest(yml):
                c, _ = parse(yml)
                self.assertTrue(all(c.check_on(n) for n in checks.HOOK_CHECKS))


class Plugin(unittest.TestCase):
    """The plugin's files, its schema and the code agree on the settings."""

    # The schema editors check a Config against lists the settings the code has, and no others.
    def test_schema_keys(self):
        s = schema()
        self.assertEqual(sorted(s["properties"]), sorted(config._KEYS))
        self.assertIs(s["additionalProperties"], False)
        self.assertTrue(names.SCHEMA.endswith("/" + names.PLUGIN_DIR + "/schema.json"))

    # The plugin's one Output style is a file in its output-styles/, and the schema has no key
    # for one (PRD no-config).
    def test_output_styles(self):
        folder = os.path.join(PLUGIN, "output-styles")
        files = sorted(f for f in os.listdir(folder) if f.endswith(".md"))
        self.assertEqual(files, ["short-replies.md"])
        self.assertNotIn("output-style", schema()["properties"])

    # Every Guideline is a file in the plugin's guidelines/, and the schema has no key for one.
    def test_guidelines(self):
        folder = os.path.join(PLUGIN, "guidelines")
        files = sorted(
            f[:-3] for f in os.listdir(folder)
            if f.endswith(".md") and os.path.isfile(os.path.join(folder, f))
        )
        want = sorted(guidelines.names())
        self.assertEqual(files, want)
        self.assertNotIn("guidelines", schema()["properties"])


if __name__ == "__main__":
    unittest.main()
