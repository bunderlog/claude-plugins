import os
import tempfile
import time
import unittest

from baloo import guidelines
from baloo.guidelines import EVERY_TASK, IN_ZSH


def write(root, files):
    """Writes each file of `files`, by its path from `root`, with its text."""
    for path, text in files.items():
        path = os.path.join(root, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def temp(test):
    d = tempfile.TemporaryDirectory()
    test.addCleanup(d.cleanup)
    return d.name


def when(name):
    return next(g.when for g in guidelines.ALL if g.name == name)


class Fitting(unittest.TestCase):
    def test_fitting(self):
        always = ["principles", "design", "testing", "debugging", "writing-for-agents"]
        for name, files, want in [
            ("no stack", {"README.md": "go.mod vue"}, always),
            (
                "go.mod at any depth",
                {"src/app/go.mod": "module app\n"},
                always + ["dependencies", "go"],
            ),
            (
                "a package.json naming typescript and vue",
                {
                    "web/package.json": '{"devDependencies": {"typescript": "^5"}, '
                    '"dependencies": {"vue": "^3"}}'
                },
                always + ["dependencies", "typescript", "vue"],
            ),
            (
                "a package.json naming tailwindcss",
                {"web/package.json": '{"devDependencies": {"tailwindcss": "^4"}}'},
                always + ["dependencies", "tailwind"],
            ),
            (
                "a package.json naming neither",
                {"package.json": '{"name": "vue", "scripts": {"typescript": "tsc"}}'},
                always + ["dependencies"],
            ),
            ("not JSON", {"package.json": '{"dependencies": {"vue": '}, always + ["dependencies"]),
            ("a Cargo.toml", {"crates/x/Cargo.toml": "[package]\n"}, always + ["dependencies"]),
            ("a pyproject.toml", {"pyproject.toml": "[project]\n"}, always + ["dependencies"]),
            (
                "a GitHub Actions workflow",
                {".github/workflows/ci.yml": "on: push\n"},
                always + ["ci"],
            ),
            ("a Jenkinsfile", {"Jenkinsfile": "pipeline {}\n"}, always + ["ci"]),
            ("a .github with no workflows", {".github/CODEOWNERS": "* @a\n"}, always),
            ("a CI's config below the root", {"tools/.gitlab-ci.yml": "test: {}\n"}, always),
            (
                "another project's code",
                {
                    "node_modules/x/package.json": '{"dependencies": {"vue": "^3"}}',
                    "vendor/x/go.mod": "module x\n",
                    ".cache/go.mod": "module x\n",
                    "tools/testdata/go.mod": "module x\n",
                    "target/web/package.json": '{"dependencies": {"vue": "^3"}}',
                    "dist/Cargo.toml": "[package]\n",
                },
                always,
            ),
        ]:
            with self.subTest(name):
                root = temp(self)
                write(root, files)
                self.assertEqual(guidelines.fitting(root), want)


class Index(unittest.TestCase):
    # In zsh, session start adds the rules zsh needs after the rules for every task.
    def test_zsh(self):
        plugin = temp(self)
        write(
            plugin,
            {
                "guidelines/principles.md": "# P\n\n"
                + EVERY_TASK
                + "\n\n- one\n\n"
                + IN_ZSH
                + "\n\n- quote globs\n\n## Next\n"
            },
        )
        for shell, want in [("zsh", True), ("bash", False), ("", False)]:
            with self.subTest(shell=shell):
                text, why = guidelines.index(plugin, {"principles": True}, shell)
                self.assertIsNone(why)
                self.assertEqual("- one\nIn zsh:\n- quote globs\n" in text, want)
        text, _ = guidelines.index(plugin, {"go": True}, "zsh")
        self.assertNotIn("zsh", text)

    def test_index(self):
        plugin = temp(self)
        self.assertEqual(guidelines.index(plugin, {"go": False}, ""), ("", None))
        # Without the rules for every task, the lines are still there; a Guideline given by the
        # file Claude works on has none.
        lines = (
            "Read a file when its task comes up:\n"
            f"- {when('principles')}: {os.path.join(plugin, 'guidelines', 'principles.md')}\n"
            f"- {when('go')}: {os.path.join(plugin, 'guidelines', 'go.md')}"
        )
        on = {"principles": True, "go": True, "vue": True, "typescript": True, "testing": True}
        text, why = guidelines.index(plugin, on, "")
        self.assertTrue(text.endswith(lines), text)
        principles = os.path.join(plugin, "guidelines", "principles.md")
        self.assertEqual(why, f"open {principles}: no such file or directory")

        write(plugin, {"guidelines/principles.md": "# P\n\n## Other\n\nx\n"})
        text, why = guidelines.index(plugin, on, "")
        self.assertTrue(text.endswith(lines), text)
        self.assertNotIn("On every task", text)
        self.assertEqual(why, f'{principles} has no "## On every task"')

        head = (
            "Guidelines, the plugin's working rules; the project's own CLAUDE.md, config and "
            "linters win where they conflict.\nOn every task:\n"
        )
        for name, file, rules in [
            (
                "LF",
                "# P\n\n" + EVERY_TASK + "\n\n- one\n- two\n\n## Next\n\nlater\n",
                "- one\n- two\n",
            ),
            (
                "CRLF",
                "# P\r\n\r\n" + EVERY_TASK + "\r\n\r\n- one\r\n- two\r\n\r\n## Next\r\n",
                "- one\n- two\n",
            ),
            (
                "a space after the heading, a deeper one inside",
                "# P\n\n" + EVERY_TASK + " \n- one\n### Sub\n- two\n",
                "- one\n### Sub\n- two\n",
            ),
            ("the heading first", EVERY_TASK + "\n- one\n", "- one\n"),
        ]:
            with self.subTest(name):
                write(plugin, {"guidelines/principles.md": file})
                self.assertEqual(guidelines.index(plugin, on, ""), (head + rules + lines, None))


class ForFile(unittest.TestCase):
    # A Guideline given by the file Claude works on comes whole, once a session, where the Config
    # turns it on, and each one given is logged.
    def test_for_file(self):
        plugin, data = temp(self), temp(self)
        write(
            plugin,
            {
                "guidelines/typescript.md": "# TypeScript\n\nNo any.\n",
                "guidelines/vue.md": "# Vue\n\nScript setup.\n",
                "guidelines/testing.md": "# Testing\n\nRed first.\n",
            },
        )
        on = {"typescript": True, "vue": True, "testing": True}
        for rel, want in [
            ("src/a.ts", ["typescript"]),
            ("src/App.vue", ["typescript", "vue"]),
            ("x/a_test.go", ["testing"]),
            ("src/a.test.ts", ["typescript", "testing"]),
            ("tests/test_a.py", ["testing"]),
            ("src/__tests__/a.js", ["testing"]),
            ("src/a.go", []),
            ("README.md", []),
            ("src/testing.ts", ["typescript"]),
        ]:
            with self.subTest(rel):
                text = guidelines.for_file(plugin, temp(self), "", rel, on)
                got = [
                    name
                    for name in ("typescript", "vue", "testing")
                    if f"The {name} Guideline applies to {rel}" in text
                ]
                self.assertEqual(got, want)

        text = guidelines.for_file(plugin, data, "s1", "src/App.vue", on)
        self.assertIn("# Vue\n\nScript setup.", text)
        self.assertIn("# TypeScript\n\nNo any.", text)
        self.assertEqual(guidelines.for_file(plugin, data, "s1", "src/b.ts", on), "")
        self.assertEqual(guidelines.for_file(plugin, data, "s2", "src/b.ts", {"vue": True}), "")
        with open(os.path.join(data, "guidelines", "guidelines.log")) as f:
            lines = f.read().strip().split("\n")
        self.assertEqual(len(lines), 2, lines)
        self.assertTrue(lines[0].endswith("\ts1\ttypescript\tsrc/App.vue"), lines)
        self.assertTrue(lines[1].endswith("\ts1\tvue\tsrc/App.vue"), lines)

    # What a session was given is forgotten after a week, so the Guideline comes again.
    def test_forgets_after_a_week(self):
        plugin, data = temp(self), temp(self)
        write(plugin, {"guidelines/typescript.md": "# TypeScript\n"})
        on = {"typescript": True}
        self.assertNotEqual(guidelines.for_file(plugin, data, "s1", "a.ts", on), "")
        seen = os.path.join(data, "guidelines", "shown", "s1")
        old = time.time() - 8 * 24 * 3600
        os.utime(seen, (old, old))
        self.assertNotEqual(guidelines.for_file(plugin, data, "s1", "b.ts", on), "")


class Readable(unittest.TestCase):
    def test_readable(self):
        plugin, elsewhere = temp(self), temp(self)
        write(plugin, {"guidelines/go.md": "# Go\n", "guidelines/sub/x.md": "x", "README.md": "r"})
        write(elsewhere, {"go.md": "# Go\n"})
        link = os.path.join(elsewhere, "link.md")
        os.symlink(os.path.join(plugin, "guidelines", "go.md"), link)
        for file, want in [
            (os.path.join(plugin, "guidelines", "go.md"), True),
            (os.path.join(plugin, "guidelines", "..", "guidelines", "go.md"), True),
            (link, True),
            (os.path.join(plugin, "guidelines", "sub", "x.md"), False),
            (os.path.join(plugin, "guidelines", "sub"), False),
            (os.path.join(plugin, "guidelines", "nope.md"), False),
            (os.path.join(plugin, "README.md"), False),
            (os.path.join(elsewhere, "go.md"), False),
            ("guidelines/go.md", False),
        ]:
            with self.subTest(file):
                self.assertEqual(guidelines.readable(plugin, file), want)
        self.assertFalse(guidelines.readable("", os.path.join(plugin, "guidelines", "go.md")))


if __name__ == "__main__":
    unittest.main()
