import os
import unittest

from baloo.checks import Error, no_conflict_markers
from tests import testkit
from tests.checks import stage

# Built at run time, so this file holds no line that opens a conflict.
OPEN, MIDDLE, CLOSE = "<" * 7, "=" * 7, ">" * 7


class NoConflictMarkers(unittest.TestCase):
    def test_finds_each_marker_the_staged_changes_add(self):
        dir = testkit.repo(self)
        stage(dir, {"a.go": f"a\n{OPEN} HEAD\nx \n{MIDDLE}\ny\n{CLOSE} topic\n"})
        self.assertEqual(no_conflict_markers(dir), ["a.go:2", "a.go:4", "a.go:6"])

    def test_passes_what_is_not_a_marker(self):
        dir = testkit.repo(self)
        stage(
            dir,
            {
                "a.md": f"Title\n{MIDDLE}\n\ntrailing space \n",
                "b.txt": f"{OPEN}< eight, not seven\n",
            },
        )
        self.assertEqual(no_conflict_markers(dir), [])

    # A file that holds markers on purpose passes with a longer conflict-marker-size in
    # .gitattributes, as git's own check reads it.
    def test_passes_a_file_with_a_longer_marker_size(self):
        dir = testkit.repo(self)
        with open(os.path.join(dir, ".gitattributes"), "w") as f:
            f.write("testdata/* conflict-marker-size=32\n")
        stage(dir, {"testdata/merge.txt": f"{OPEN} ours\n"})
        self.assertEqual(no_conflict_markers(dir), [])

    def test_passes_nothing_staged(self):
        self.assertEqual(no_conflict_markers(testkit.repo(self)), [])

    def test_fails_outside_a_repo(self):
        with self.assertRaises(Error):
            no_conflict_markers(testkit.tempdir(self))


if __name__ == "__main__":
    unittest.main()
