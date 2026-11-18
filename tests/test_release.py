import importlib.util
import json
import os
import sys
import unittest

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

    # A breaking footer's wrapped lines become one paragraph indented under the change's line,
    # up to the blank line before `PRD x`; the `!`-only change, the feature and the fix keep
    # their lines.
    def test_breaking_footer(self):
        commits = [
            Commit("a1", "feat!: a breaking feature"),
            Commit("b2", "refactor: x\n\nWhat changed, in a body.\n\n"
                         "BREAKING CHANGE: install y (claude plugin install y@m)\n"
                         "to keep the Checks, and pick y:style\n"
                         "in place of x:style.\n\nPRD x"),
            Commit("c3", "chore(config): move it\n\nBREAKING-CHANGE: set z again.\nRefs #4"),
            Commit("d4", "feat(status-line): a feature\n\nwith a body"),
            Commit("e5", "fix: a fix"),
        ]
        want = """## 0.4.0 — 2026-09-29

### Breaking changes

- a breaking feature (a1)
- x (b2)

  install y (claude plugin install y@m) to keep the Checks, and pick y:style in place of x:style.

- config: move it (c3)

  set z again.

### Features

- status-line: a feature (d4)

### Fixes

- a fix (e5)
"""
        self.assertEqual(release.section("0.4.0", "2026-09-29", commits), want)

    def test_breaking_footer_in_every_plugin(self):
        both = Commit("b2", "refactor: x\n\nBREAKING CHANGE: install y\nnow.\n\nPRD x")
        want = """## 0.4.0 — 2026-09-29

### baloo

#### Breaking changes

- x (b2)

  install y now.

#### Fixes

- a fix (a1)

### louie

#### Breaking changes

- x (b2)

  install y now.
"""
        got = release.sections(
            "0.4.0", "2026-09-29", {"baloo": [Commit("a1", "fix: a fix"), both], "louie": [both]}
        )
        self.assertEqual(got, want)


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def commit(root, rel, text, message):
    write(root, rel, text)
    testkit.git(root, "add", rel)
    testkit.git(root, "commit", "-q", "-m", message)


MANIFEST = "plugins/baloo/.claude-plugin/plugin.json"


def released(test, names=("baloo",)):
    """A repo whose last Release is v0.3.1 of the marketplace's plugins `names`, with a
    CHANGELOG."""
    root = testkit.repo(test)
    write(root, release.MARKETPLACE, json.dumps({"name": "m", "plugins": [
        {"name": n, "source": "./plugins/" + n} for n in names
    ]}))
    for n in names:
        write(root, f"plugins/{n}/.claude-plugin/plugin.json",
              json.dumps({"name": n, "version": "0.3.1"}, indent=2) + "\n")
    write(root, "CHANGELOG.md", release.CHANGELOG_HEADER + "\n## 0.3.1 — 2026-09-01\n\nOld.\n")
    testkit.git(root, "add", ".")
    testkit.git(root, "commit", "-q", "-m", "chore(release): 0.3.1")
    testkit.git(root, "tag", "v0.3.1")
    return root


class SiteChanges(unittest.TestCase):
    def _changes(self, by_plugin):
        changelog = release.CHANGELOG_HEADER + "\n" + release.sections("0.71.0", "2026-11-19", by_plugin)
        return release.site_changes(release.release_notes(changelog, "0.71.0"))

    def test_names_each_feature_and_breaking_change_once_after_its_plugins(self):
        self.assertEqual(self._changes({
            "baloo": [Commit("a1", "fix: a fix")],
            "louie": [Commit("b2", "feat: add /louie:x"), Commit("c3", "fix: another")],
            "bagheera": [Commit("d4", "feat!: drop a Check\n\nBREAKING CHANGE: it is gone"), Commit("e5", "feat: rename a word")],
            "louie2": [Commit("e5", "feat: rename a word")],
        }), [
            "- louie: add /louie:x (b2)",
            "- bagheera: drop a Check (d4)",
            "- bagheera, louie2: rename a word (e5)",
        ])

    def test_one_plugins_notes_name_no_plugin(self):
        self.assertEqual(self._changes({"baloo": [Commit("a1", "feat: a skill")]}), ["- a skill (a1)"])

    def test_fixes_alone_give_none(self):
        self.assertEqual(self._changes({
            "baloo": [Commit("a1", "fix: a fix")], "louie": [], "bagheera": [Commit("b2", "docs: words")],
        }), [])

    def test_release_notes_are_the_versions_section_alone(self):
        changelog = release.CHANGELOG_HEADER + "\n## 0.2.0 — d\n\n- b\n\n## 0.1.0 — d\n\n- a\n"
        self.assertEqual(release.release_notes(changelog, "0.2.0"), "\n- b\n\n")
        self.assertEqual(release.release_notes(changelog, "0.1.0"), "\n- a\n")
        self.assertEqual(release.release_notes(changelog, "0.3.0"), "")


class Release(unittest.TestCase):
    # Only the plugin's commits count: not the tests or the release tool; the commit
    # and the files are made, and the tag, which must be signed, fails without a key.
    def test_release(self):
        root = released(self)
        commit(root, "tests/test_x.py", "x", "feat: a test only")
        commit(root, "src/release/release.py", "x", "feat: the tool only")
        commit(root, "plugins/baloo/skills/x/SKILL.md", "x", "fix(skills): a fix")
        sha = testkit.git(root, "rev-parse", "--short", "HEAD").strip()
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertTrue(
            str(caught.exception).startswith(
                "the release tag failed: fix what failed, then "
                "`git tag -s v0.3.2 -m v0.3.2 && git push --atomic origin main v0.3.2`: "
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
        self.assertEqual(release.version(root), "0.3.2")

    def test_nothing_to_release(self):
        root = released(self)
        commit(root, "tests/test_x.py", "x", "feat: a test only")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(
            str(caught.exception),
            "nothing to release: plugins/baloo is unchanged since v0.3.1",
        )

    def test_uncommitted_changes(self):
        root = released(self)
        write(root, "README.md", "changed\n")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(str(caught.exception), "commit or stash your changes first")

    def test_tag_and_manifest_disagree(self):
        root = released(self)
        commit(root, MANIFEST, '{"version": "0.4.0"}\n', "chore: bump by hand")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-10-14")
        self.assertEqual(
            str(caught.exception),
            "the last tag is v0.3.1, but the plugins' manifests say 0.4.0",
        )


    # With two plugins, one Release raises both to one version, a commit counting for the plugin
    # it changes, under that plugin's part of the CHANGELOG (ADR releases).
    def test_two_plugins(self):
        root = released(self, ("baloo", "louie"))
        commit(root, "plugins/baloo/skills/x/SKILL.md", "x", "fix(skills): a fix")
        fix = testkit.git(root, "rev-parse", "--short", "HEAD").strip()
        commit(root, "plugins/louie/skills/y/SKILL.md", "y", "feat: a workflow")
        feat = testkit.git(root, "rev-parse", "--short", "HEAD").strip()
        with self.assertRaises(release.Error):  # the tag, without a key
            release.release(root, "2026-11-10")
        self.assertEqual(release.version(root), "0.4.0")
        with open(os.path.join(root, "CHANGELOG.md")) as f:
            self.assertIn(
                f"\n## 0.4.0 — 2026-11-10\n\n### baloo\n\n#### Fixes\n\n- skills: a fix ({fix})\n"
                f"\n### louie\n\n#### Features\n\n- a workflow ({feat})\n",
                f.read(),
            )

    # Plugins whose manifests disagree on the version make no Release.
    def test_versions_differ(self):
        root = released(self, ("baloo", "louie"))
        commit(root, "plugins/louie/.claude-plugin/plugin.json", '{"version": "0.1.0"}\n', "chore: x")
        with self.assertRaises(release.Error) as caught:
            release.release(root, "2026-11-10")
        self.assertEqual(
            str(caught.exception), "the plugins' versions differ: baloo 0.3.1, louie 0.1.0"
        )


CI_YML = """name: CI

on:
  push:
    branches: [main]
    paths:
      - '**'
      - '!.about/**'
      - '!*.md'
"""

TEMPLATE_YML = """name: Template

on:
  push:
    branches: [main]
    paths:
      - 'tpl/**'
"""


class CIGreen(unittest.TestCase):
    """The check before a Release (ADR releases): each workflow's newest run on what it checks
    passed, a commit it ignores needing none."""

    def setUp(self):
        self.root = testkit.repo(self)
        write(self.root, ".github/workflows/ci.yml", CI_YML)
        write(self.root, ".github/workflows/template.yml", TEMPLATE_YML)
        write(self.root, ".github/workflows/release.yml",
              "name: Release\n\non:\n  push:\n    tags: [\"v*\"]\n")
        testkit.git(self.root, "add", ".")
        testkit.git(self.root, "commit", "-q", "-m", "ci: workflows")
        self.code = self.commit("app.py", "feat: the app")

    def commit(self, rel, message):
        commit(self.root, rel, message, message)
        return testkit.git(self.root, "rev-parse", "HEAD").strip()

    def green(self, runs):
        release.ci_green(self.root, runs)

    def refused(self, runs):
        with self.assertRaises(release.Error) as caught:
            self.green(runs)
        return str(caught.exception)

    def test_a_passed_run_on_head_and_a_workflow_with_nothing_to_check(self):
        self.green({"CI": {self.code: ("completed", "success")}})

    def test_a_commit_the_workflow_ignores_needs_no_run(self):
        self.commit(".about/inbox.md", "docs: an item")
        self.commit("README.md", "docs: the readme")
        self.green({"CI": {self.code: ("completed", "success")}})

    def test_a_commit_with_no_run_running_or_failed_is_refused(self):
        head = self.commit("lib.py", "fix: the lib")
        short = head[:7]
        self.assertEqual(
            self.refused({"CI": {self.code: ("completed", "success")}}),
            f"CI has no run on {short}, which it checks: push main and wait for it",
        )
        self.assertEqual(
            self.refused({"CI": {head: ("in_progress", "")}}),
            f"CI is still running on {short}: wait for it",
        )
        self.assertEqual(
            self.refused({"CI": {head: ("completed", "failure")}}),
            f"CI ended failure on {short}: fix it first",
        )

    def test_each_workflow_by_its_own_paths(self):
        tpl = self.commit("tpl/a.go", "feat: the template")
        self.assertEqual(
            self.refused({"CI": {tpl: ("completed", "success")}}),
            f"Template has no run on {tpl[:7]}, which it checks: push main and wait for it",
        )
        self.commit("app.py", "fix: the app again")
        head = testkit.git(self.root, "rev-parse", "HEAD").strip()
        self.green({"CI": {head: ("completed", "success")}, "Template": {tpl: ("completed", "success")}})


if __name__ == "__main__":
    unittest.main()
