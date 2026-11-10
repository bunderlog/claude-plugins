import os
import tempfile
import unittest

from bagheera import names, settings


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


if __name__ == "__main__":
    unittest.main()
