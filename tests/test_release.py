import importlib.util
import json
import os
import sys
import unittest

from baloo import names
from tests import testkit

_spec = importlib.util.spec_from_file_location(
    "release",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "release", "release.py"),
)
release = importlib.util.module_from_spec(_spec)
sys.modules["release"] = release  # a dataclass looks its module up there
_spec.loader.exec_module(release)
Commit = release.Commit


class NextVersion(unittest.TestCase):
    def test_next_version(self):
        fix = Commit("a1", "fix: a fix")
        feat = Commit("b2", "feat(status-line): a feature")
        bang = Commit("c3", "refactor!: a breaking change")
        footer = Commit("d4", "chore: tidy\n\nBREAKING CHANGE: the config moved")
        docs = Commit("e5", "docs: words")
        for version, commits, changed, want in [
            ("0.3.1", [fix], False, ""),
            ("0.3.1", [docs], True, "0.3.2"),
            ("0.3.1", [fix], True, "0.3.2"),
            ("0.3.1", [fix, feat], True, "0.4.0"),
            ("0.3.1", [bang], True, "0.4.0"),
            ("0.3.1", [footer], True, "0.4.0"),
            ("1.3.1", [feat], True, "1.4.0"),
            ("1.3.1", [feat, bang], True, "2.0.0"),
            ("0.0.0", [feat], True, "0.1.0"),
        ]:
            with self.subTest(version=version, commits=commits, changed=changed):
                self.assertEqual(release.next_version(version, commits, changed), want)

    def test_a_version_without_a_patch(self):
        with self.assertRaises(release.Error) as caught:
            release.next_version("1.2", [], True)
        self.assertEqual(str(caught.exception), 'version "1.2" is not major.minor.patch')


class Section(unittest.TestCase):
    def test_section(self):
        commits = [
            Commit("a1", "fix: a fix"),
            Commit("b2", "feat(status-line): a feature\n\nwith a body"),
            Commit("c3", "docs: words"),
            Commit("d4", "feat!: a breaking feature"),
        ]
        want = """## 0.4.0 — 2026-09-29

### Breaking changes

- a breaking feature (d4)

### Features

- status-line: a feature (b2)

### Fixes

- a fix (a1)
"""
        self.assertEqual(release.section("0.4.0", "2026-09-29", commits), want)
        self.assertEqual(
            release.section("0.4.1", "2026-09-29", commits[2:3]),
            "## 0.4.1 — 2026-09-29\n\nNo feature changes or fixes.\n",
        )


class Pin(unittest.TestCase):
    # The README's CI recipe pins the Release's commit, named with its version; nothing else in it
    # changes.
    def test_pin(self):
        readme = (
            "Pin it:\n\n```sh\nset -e\ncommit=aaa # v0.9.0\ndir=$(mktemp -d)\n```\n\n"
            "commit=aaa # v0.9.0 in prose.\n"
        )
        want = (
            "Pin it:\n\n```sh\nset -e\ncommit=bbb # v0.10.0\ndir=$(mktemp -d)\n```\n\n"
            "commit=aaa # v0.9.0 in prose.\n"
        )
        self.assertEqual(release.pin(readme, "0.10.0", "bbb"), want)

    # A README with no line to pin, or more than one, is an error rather than a Release that
    # leaves the recipe behind.
    def test_not_one_line(self):
        for readme, n in [
            ("no recipe\n", 0),
            ("version=0.9.0\n", 0),
            ("  commit=aaa # v0.9.0\n", 0),
            ("commit=aaa # v0.9.0\r\n", 0),
            ("commit=aaa # v0.9.0\ncommit=aaa # v0.9.0\n", 2),
        ]:
            with self.subTest(readme=readme):
                with self.assertRaises(release.Error) as caught:
                    release.pin(readme, "0.10.0", "bbb")
                self.assertEqual(
                    str(caught.exception),
                    f"README.md has {n} lines `commit=<sha> # v<version>` for its CI recipe; "
                    "want one",
                )


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def commit(root, rel, text, message):
    write(root, rel, text)
    testkit.git(root, "add", rel)
    testkit.git(root, "commit", "-q", "-m", message)


def released(test):
    """A repo whose last Release is v0.3.1, with a README to pin and a CHANGELOG."""
    root = testkit.repo(test)
    write(root, names.MANIFEST, json.dumps({"name": "baloo", "version": "0.3.1"}, indent=2) + "\n")
    write(root, "README.md", "```sh\ncommit=aaa # v0.3.0\n```\n")
    write(root, "CHANGELOG.md", release.CHANGELOG_HEADER + "\n## 0.3.1 — 2026-09-01\n\nOld.\n")
    testkit.git(root, "add", ".")
    testkit.git(root, "commit", "-q", "-m", "chore(release): 0.3.1")
    testkit.git(root, "tag", "v0.3.1")
    return root


class Release(unittest.TestCase):
    # Only the plugin's commits count: not its schema, the tests or the release tool; the commit
    # and the files are made, and the tag, which must be signed, fails without a key.
    def test_release(self):
        root = released(self)
        commit(root, "tests/test_x.py", "x", "feat: a test only")
        commit(root, names.PLUGIN_DIR + "/schema.json", "{}", "feat: the schema only")
        commit(root, "src/release/release.py", "x", "feat: the tool only")
        commit(root, names.PLUGIN_DIR + "/skills/x/SKILL.md", "x", "fix(skills): a fix")
        sha = testkit.git(root, "rev-parse", "--short", "HEAD").strip()
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertTrue(
            str(caught.exception).startswith(
                "the release tag failed: fix what failed, then "
                "`git tag -s v0.3.2 -m v0.3.2 && python3 src/release/release.py pin && "
                "git push --atomic origin main v0.3.2`: "
            ),
            caught.exception,
        )
        self.assertEqual(
            testkit.git(root, "log", "-1", "--format=%s").strip(), "chore(release): 0.3.2"
        )
        with open(os.path.join(root, "CHANGELOG.md")) as f:
            self.assertEqual(
                f.read(),
                release.CHANGELOG_HEADER
                + f"\n## 0.3.2 — 2026-10-14\n\n### Fixes\n\n- skills: a fix ({sha})\n"
                + "\n## 0.3.1 — 2026-09-01\n\nOld.\n",
            )
        # The README pins the tag's commit only in a commit after it, which a failed tag never
        # makes.
        with open(os.path.join(root, "README.md")) as f:
            self.assertEqual(f.read(), "```sh\ncommit=aaa # v0.3.0\n```\n")
        self.assertEqual(release.version(root), "0.3.2")

    # After the tag, a commit of its own pins the README's CI recipe to the tagged commit, which
    # the tagged commit can't name.
    def test_pin_release(self):
        root = released(self)
        tagged = testkit.git(root, "rev-parse", "v0.3.1").strip()
        release.pin_release(root, "0.3.1")
        with open(os.path.join(root, "README.md")) as f:
            self.assertEqual(f.read(), f"```sh\ncommit={tagged} # v0.3.1\n```\n")
        self.assertEqual(
            testkit.git(root, "log", "-1", "--format=%s").strip(),
            "docs: pin the README's CI recipe to v0.3.1",
        )
        self.assertEqual(testkit.git(root, "rev-parse", "HEAD~1").strip(), tagged)

    def test_nothing_to_release(self):
        root = released(self)
        commit(root, "tests/test_x.py", "x", "feat: a test only")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(
            str(caught.exception),
            "nothing to release: plugins/baloo :!plugins/baloo/schema.json is unchanged since "
            "v0.3.1",
        )

    def test_uncommitted_changes(self):
        root = released(self)
        write(root, "README.md", "changed\n")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(str(caught.exception), "commit or stash your changes first")

    def test_tag_and_manifest_disagree(self):
        root = released(self)
        commit(root, names.MANIFEST, '{"version": "0.4.0"}\n', "chore: bump by hand")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(
            str(caught.exception),
            "the last tag is v0.3.1, but plugins/baloo/.claude-plugin/plugin.json says 0.4.0",
        )


if __name__ == "__main__":
    unittest.main()
