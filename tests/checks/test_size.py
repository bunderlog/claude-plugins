import unittest

from baloo.checks import Error, no_large_files
from tests import testkit
from tests.checks import stage


class NoLargeFiles(unittest.TestCase):
    def test_finds_an_added_file_over_the_limit(self):
        dir = testkit.repo(self)
        stage(dir, {"bin/app": "x" * (3 * 1024 + 1), "small.go": "x" * (3 * 1024)})
        self.assertEqual(no_large_files(dir, 3), ["bin/app: 4 KB, over 3 KB"])

    # Without a limit of its own, a file may be 1 MB.
    def test_limits_a_file_to_1_mb_by_default(self):
        dir = testkit.repo(self)
        stage(dir, {"a": "x" * (1024 * 1024)})
        self.assertEqual(no_large_files(dir, 0), [])
        stage(dir, {"b": "x" * (1024 * 1024 + 1)})
        self.assertEqual(no_large_files(dir, 0), ["b: 1025 KB, over 1024 KB"])

    # A file already committed passes when it changes or moves: it was let in once.
    def test_passes_a_file_already_committed(self):
        dir = testkit.repo(self)
        big = "x" * (4 * 1024)
        stage(dir, {"data.bin": big})
        testkit.git(dir, "commit", "-q", "-m", "chore: data")
        stage(dir, {"data.bin": big + "y"})
        testkit.git(dir, "mv", "data.bin", "moved.bin")
        self.assertEqual(no_large_files(dir, 1), [])

    def test_fails_outside_a_repo(self):
        with self.assertRaises(Error):
            no_large_files(testkit.tempdir(self), 0)


if __name__ == "__main__":
    unittest.main()
