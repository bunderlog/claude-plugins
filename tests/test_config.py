import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from baloo import checks, config, guidelines, names, statusline
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
            self.assertEqual(f.read(), config._new_config(guidelines.fitting(root)))
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

    # A new Config turns on the Guidelines for any project, and a stack's only where the repo has
    # it.
    def test_new_config_guidelines(self):
        root, sub = self.temp_repo()
        with open(os.path.join(sub, "go.mod"), "w") as f:
            f.write("module x\n")
        c, _, problems = config.load(root)
        want = {
            "principles": True, "design": True, "testing": True, "debugging": True,
            "writing-for-agents": True, "ci": False, "dependencies": True, "go": True,
            "typescript": False, "vue": False, "tailwind": False,
        }
        self.assertEqual((c.guidelines, problems), (want, []))

    # A new Config turns every Check on.
    def test_new_config_checks(self):
        root, _ = self.temp_repo()
        c, _, problems = config.load(root)
        for name in checks.GIT_HOOK_CHECKS + checks.HOOK_CHECKS:
            self.assertIs(c.checks.get(name), True, name)
        self.assertEqual(problems, [])


class Read(Case):
    # Read reads a Config as Load does, but never creates one.
    def test_never_creates(self):
        root, sub = self.temp_repo()
        c = config.read(sub)
        self.assertEqual(c.root, root)
        self.assertTrue(c.check_on("no-secrets-in-context"))
        self.assertFalse(os.path.exists(os.path.join(root, names.CONFIG)))
        self.write_config(root, "claude-hooks:\n  no-secrets-in-context: false\n")
        self.assertFalse(config.read(sub).check_on("no-secrets-in-context"))

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
            ("a new config", config._new_config(guidelines.names()), []),
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

    # A new Config's guidelines, claude-hooks and git-hooks list their keys sorted.
    def test_new_config_sorted(self):
        from baloo import yaml

        top = yaml.parse(config._new_config([]))
        maps = [(k.text, [kk.text for kk, _ in v.pairs]) for k, v in top.pairs if v.tag == "map"]
        self.assertEqual([k for k, _ in maps], ["guidelines", "claude-hooks", "git-hooks"])
        for key, keys in maps:
            self.assertEqual(keys, sorted(keys), key)


class Settings(Case):
    def test_output_style(self):
        for yml, style, problems in [
            ("output-style: short-replies\n", "short-replies", 0),
            ("output-style: false\n", "", 0),
            ("output-style: true\n", "", 1),
            ("output-style: nope\n", "", 1),
            ("output-style: [short-replies]\n", "", 1),
            ("# none\n", "", 0),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.output_style, len(got)), (style, problems))

    def test_status_line(self):
        want_problem = (
            ".claude/baloo.yml line 1: status-line: is not true, false or its bars and thresholds;"
            " the Status line is left as it is"
        )
        for yml, on, problems in [
            ("status-line: true\n", True, []),
            ("status-line: false\n", False, []),
            ("status-line: yes please\n", None, [want_problem]),
            ("status-line: [context]\n", None, [want_problem]),
            ("status-line: {}\n", True, []),
            ("# none\n", None, []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.status_line, got), (on, problems))
        self.assertIsNone(parse("status-line: true\n")[0].status_layout)

    # The Status line takes its bars, in order, and their thresholds; a wrong one is a problem,
    # and its default applies, a wrong bar in the list left out. Without them the default Layout
    # applies.
    def test_status_layout(self):
        t = statusline.Thresholds
        default = {
            "context": t(yellow=15, red=20), "cache": t(yellow=40, red=20),
            "5h": t(yellow=70, red=85), "7d": t(yellow=80, red=95),
        }
        every = ["context", "5h", "7d", "cache"]
        for yml, bars, thresholds, problems in [
            ("status-line: {}\n", every, default, []),
            (
                "status-line:\n  bars: [7d, context]\n  thresholds:\n    context: {red: 50}\n"
                "    cache: {yellow: 50, red: 10}\n",
                ["7d", "context"],
                dict(default, context=t(yellow=15, red=50), cache=t(yellow=50, red=10)),
                [],
            ),
            ("status-line:\n  bars: []\n", [], default, []),
            (
                "status-line:\n  bars:\n    - context\n    - ctx\n    - context\n  thresholds:\n"
                "    context: {yellow: 30, red: 20}\n    cache: {yellow: 10, red: 20}\n"
                "    5h: {yellow: 101}\n    7d: {blue: 1}\n    week: {red: 1}\n  colors: true\n",
                ["context"],
                default,
                [
                    ".claude/baloo.yml line 4: status-line.bars: ctx is not one of context, 5h, 7d,"
                    " cache; ignored",
                    ".claude/baloo.yml line 5: status-line.bars: context is there twice; ignored",
                    ".claude/baloo.yml line 7: status-line.thresholds.context: turns red before"
                    " yellow; its default applies",
                    ".claude/baloo.yml line 8: status-line.thresholds.cache: turns red before"
                    " yellow; its default applies",
                    ".claude/baloo.yml line 9: status-line.thresholds.5h: is not { yellow:"
                    " <percent>, red: <percent> }; its default applies",
                    ".claude/baloo.yml line 10: status-line.thresholds.7d: is not { yellow:"
                    " <percent>, red: <percent> }; its default applies",
                    ".claude/baloo.yml line 11: status-line.thresholds.week is not one of context,"
                    " 5h, 7d, cache; ignored",
                    ".claude/baloo.yml line 12: status-line.colors is not a setting of"
                    " status-line; ignored",
                ],
            ),
            (
                "status-line:\n  bars: context\n  thresholds: [1]\n",
                every,
                default,
                [
                    ".claude/baloo.yml line 2: status-line.bars: is not a list of context, 5h, 7d,"
                    " cache; its default applies",
                    ".claude/baloo.yml line 3: status-line.thresholds: is not a map of bars to"
                    " thresholds; its default applies",
                ],
            ),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertIs(c.status_line, True)
                layout = c.status_layout
                self.assertEqual((layout.bars, layout.thresholds, got), (bars, thresholds, problems))

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
            (config._new_config([]), True, []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.session_review, got), (on, problems))

    # Each Guideline turns on with its own key under guidelines, and a wrong entry is a problem at
    # its own line while the entries beside it apply.
    def test_guidelines(self):
        for yml, on, problems in [
            ("guidelines:\n  principles: true\n  go: true\n  vue: false\n", ["go", "principles"],
             []),
            ("guidelines:\n", [], []),
            ("guidelines:\n  nope: true\n  go: yes please\n  design: true\n", ["design"], [
                ".claude/baloo.yml line 2: guidelines.nope is not a guideline; ignored",
                ".claude/baloo.yml line 3: guidelines.go: is not true or false; its default"
                " applies",
            ]),
            ("guidelines: true\n", [], [
                ".claude/baloo.yml line 1: guidelines: is not a map of guidelines to true or"
                " false; its default applies",
            ]),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual(
                    (sorted(n for n, ok in c.guidelines.items() if ok), got), (on, problems)
                )

    # A setting an earlier Release had is no problem: the Config works as without it, the settings
    # beside it apply, and doctor gets a line naming it to delete (ADR measurement).
    def test_removed(self):
        yml = (
            "stop-check: mise run check\nclaude-hooks:\n  no-destructive-commands: true\n"
            "  no-secrets-in-context: false\nformat-on-edit: npx prettier --write\n"
        )
        c, problems = parse(yml)
        self.assertEqual(problems, [])
        self.assertEqual(c.removed, [
            ".claude/baloo.yml line 1: stop-check is no longer a setting and is ignored: delete it",
            ".claude/baloo.yml line 3: claude-hooks.no-destructive-commands is no longer a setting"
            " and is ignored: delete it",
        ])
        self.assertFalse(c.check_on("no-secrets-in-context"))
        self.assertEqual(c.format_on_edit, "npx prettier --write")
        self.assertNotIn("stop-check", config._new_config([]))
        self.assertNotIn("no-destructive-commands", config._new_config([]))

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
            (config._new_config([]), "", []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.format_on_edit, got), (command, problems))
        self.assertIn("\n# format-on-edit: npx prettier --write\n", config._new_config([]))

    # git-hook-commands names, by Git hook, the project's own command it runs after its Checks; a
    # hook the plugin doesn't write, or a value that isn't a command or false, is a problem at its
    # own line while the entries beside it apply, and a new Config has it only as a comment (ADR
    # git-hooks).
    def test_git_hook_commands(self):
        for yml, commands, problems in [
            ("git-hook-commands:\n  pre-commit: mise run test\n  pre-push: false\n",
             {"pre-commit": "mise run test"}, []),
            ("git-hook-commands:\n  post-merge: npm ci\n  pre-commit: [x]\n"
             "  commit-msg: npx commitlint --edit $1\n",
             {"commit-msg": "npx commitlint --edit $1"}, [
                ".claude/baloo.yml line 2: git-hook-commands.post-merge is not a Git hook of the"
                " plugin's; ignored",
                ".claude/baloo.yml line 3: git-hook-commands.pre-commit: is not a command or false;"
                " its default applies",
             ]),
            ("git-hook-commands: mise run test\n", {}, [
                ".claude/baloo.yml line 1: git-hook-commands: is not a map of Git hooks to"
                " commands; its default applies",
            ]),
            (config._new_config([]), {}, []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.git_hook_commands, got), (commands, problems))
        self.assertIn("\n# git-hook-commands:\n#   pre-commit: mise run test\n",
                      config._new_config([]))
        c, _ = parse("git-hook-commands:\n  pre-commit: mise run test\n")
        self.assertTrue(c.git_hook_runs("git-hook-commands.pre-commit"))
        self.assertFalse(c.git_hook_runs("git-hook-commands.pre-push"))
        self.assertFalse(c.git_hook_runs("conventional-commits"))

    # Each Check turns on or off with its own key under the group that runs it, and a wrong entry
    # is a problem at its own line while the entries beside it apply. Without its key, a Check a
    # Hook runs is on and a Git hook's is off (ADR checks).
    def test_checks(self):
        hooks = ["no-git-hook-bypass", "no-secrets-in-context"]
        for yml, on, problems in [
            ("git-hooks:\n  no-ai-coauthor: true\nclaude-hooks:\n  no-secrets-in-context: false\n",
             ["no-ai-coauthor", "no-git-hook-bypass"], []),
            ("", hooks, []),
            ("claude-hooks:\ngit-hooks:\n", hooks, []),
            ("git-hooks:\n  nope: true\n  linear-history: yes please\n"
             "  no-secrets-in-context: false\nclaude-hooks:\n  no-git-hook-bypass: false\n"
             "  no-ai-coauthor: true\n",
             ["no-secrets-in-context"], [
                ".claude/baloo.yml line 2: git-hooks.nope is not a check; ignored",
                ".claude/baloo.yml line 3: git-hooks.linear-history: is not true or false; its"
                " default applies",
                ".claude/baloo.yml line 4: git-hooks.no-secrets-in-context is not a check; ignored",
                ".claude/baloo.yml line 7: claude-hooks.no-ai-coauthor is not a check; ignored",
             ]),
            ("git-hooks: true\n", hooks, [
                ".claude/baloo.yml line 1: git-hooks: is not a map of checks to true or false; its"
                " default applies",
            ]),
            ("checks:\n  no-ai-coauthor: true\n", hooks, [
                ".claude/baloo.yml line 1: checks is not a setting; ignored",
            ]),
            ("git-hooks:\n  conventional-commits:\n    types: any\n",
             ["conventional-commits", "no-git-hook-bypass", "no-secrets-in-context"], []),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                every = checks.GIT_HOOK_CHECKS + checks.HOOK_CHECKS
                self.assertEqual((sorted(n for n in every if c.check_on(n)), got), (on, problems))

    # conventional-commits takes its types, a list or any, and its longest line, 0 for none; a
    # wrong setting is a problem, and its default applies.
    def test_conventional_commits(self):
        rules = checks.CommitRules
        for yml, want, problems in [
            ("git-hooks:\n  conventional-commits: true\n", rules(), []),
            ("git-hooks:\n  conventional-commits:\n    types: [feat, fix]\n    max-length: 72\n",
             rules(types=["feat", "fix"], max_length=72), []),
            ("git-hooks:\n  conventional-commits:\n    types: any\n    max-length: 0\n",
             rules(any_type=True, max_length=0), []),
            ("git-hooks:\n  conventional-commits:\n    types: some\n    max-length: -1\n"
             "    nope: 1\n", rules(), [
                ".claude/baloo.yml line 3: git-hooks.conventional-commits.types: is not a list of"
                " types or any; its default applies",
                ".claude/baloo.yml line 4: git-hooks.conventional-commits.max-length: is not a"
                " length of 0 or more; its default applies",
                ".claude/baloo.yml line 5: git-hooks.conventional-commits.nope is not a setting of"
                " conventional-commits; ignored",
             ]),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.commit_rules, got), (want, problems))
                self.assertTrue(c.check_on("conventional-commits"))

    # no-large-files takes its limit, in KB, of 1 or more; a wrong setting is a problem, and its
    # default applies.
    def test_no_large_files(self):
        for yml, max_kb, problems in [
            ("git-hooks:\n  no-large-files: true\n", 0, []),
            ("git-hooks:\n  no-large-files:\n    max-size: 5000\n", 5000, []),
            ("git-hooks:\n  no-large-files:\n    max-size: 0\n    nope: 1\n", 0, [
                ".claude/baloo.yml line 3: git-hooks.no-large-files.max-size: is not a size of 1"
                " KB or more; its default applies",
                ".claude/baloo.yml line 4: git-hooks.no-large-files.nope is not a setting of"
                " no-large-files; ignored",
            ]),
        ]:
            with self.subTest(yml):
                c, got = parse(yml)
                self.assertEqual((c.max_file_kb, got), (max_kb, problems))
                self.assertTrue(c.check_on("no-large-files"))


class Plugin(unittest.TestCase):
    """The plugin's files, its schema and the code agree on the settings."""

    # The schema editors check a Config against lists the settings the code has, and no others.
    def test_schema_keys(self):
        s = schema()
        self.assertEqual(sorted(s["properties"]), sorted(config._KEYS))
        self.assertIs(s["additionalProperties"], False)
        self.assertTrue(names.SCHEMA.endswith("/" + names.PLUGIN_DIR + "/schema.json"))

    # Every Output style the Config can name is a file in the plugin's output-styles/, and the
    # schema names the same.
    def test_output_styles(self):
        folder = os.path.join(PLUGIN, "output-styles")
        files = sorted(
            f[:-3] for f in os.listdir(folder)
            if f.endswith(".md") and os.path.isfile(os.path.join(folder, f))
        )
        self.assertEqual(files, sorted(config.OUTPUT_STYLES))
        enum = [v for v in schema()["properties"]["output-style"]["enum"] if isinstance(v, str)]
        self.assertEqual(enum, config.OUTPUT_STYLES)

    # Every Guideline is a file in the plugin's guidelines/, and the schema has a key for each.
    def test_guidelines(self):
        folder = os.path.join(PLUGIN, "guidelines")
        files = sorted(
            f[:-3] for f in os.listdir(folder)
            if f.endswith(".md") and os.path.isfile(os.path.join(folder, f))
        )
        want = sorted(guidelines.names())
        self.assertEqual(files, want)
        g = schema()["properties"]["guidelines"]
        self.assertEqual(sorted(g["properties"]), want)
        self.assertIs(g["additionalProperties"], False)

    # The schema has a key for each Check under the group that runs it.
    def test_checks(self):
        props = schema()["properties"]
        for group, want in [
            ("claude-hooks", checks.HOOK_CHECKS),
            ("git-hooks", checks.GIT_HOOK_CHECKS),
        ]:
            with self.subTest(group):
                self.assertEqual(sorted(props[group]["properties"]), sorted(want))


if __name__ == "__main__":
    unittest.main()
