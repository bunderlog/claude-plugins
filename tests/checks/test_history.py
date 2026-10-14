import unittest

from baloo.checks import Error, linear_history
from tests import testkit

ZERO = "0" * 40


def commit(dir: str, message: str) -> str:
    """Makes an empty commit in the repo `dir` and returns it."""
    testkit.git(dir, "commit", "-q", "--allow-empty", "-m", message)
    return testkit.git(dir, "rev-parse", "HEAD").strip()


def push(local: str, remote: str) -> str:
    """The line git gives pre-push for pushing `local` to main, where the remote had `remote`."""
    return f"refs/heads/main {local} refs/heads/main {remote}\n"


def push_feature(local: str, remote: str) -> str:
    """The line git gives pre-push for pushing `local` to feature, where the remote had `remote`."""
    return f"refs/heads/feature {local} refs/heads/feature {remote}\n"


def with_merge(dir: str, branch: str, start: str) -> str:
    """Makes a branch `branch` from `start` with a merge commit of its own, and returns the
    merge."""
    testkit.git(dir, "checkout", "-q", "-b", branch, start)
    testkit.git(dir, "checkout", "-q", "-b", branch + "-topic")
    commit(dir, "feat: topic")
    testkit.git(dir, "checkout", "-q", branch)
    testkit.git(dir, "merge", "-q", "--no-ff", "-m", "Merge topic", branch + "-topic")
    return testkit.git(dir, "rev-parse", "HEAD").strip()


class LinearHistory(unittest.TestCase):
    def history(self):
        """A repo whose main has a merge commit, with the commits before it, of it and after it."""
        dir = testkit.repo(self)
        base = commit(dir, "feat: base")
        testkit.git(dir, "checkout", "-q", "-b", "side")
        commit(dir, "feat: side")
        testkit.git(dir, "checkout", "-q", "main")
        commit(dir, "feat: main")
        testkit.git(dir, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
        merge = testkit.git(dir, "rev-parse", "HEAD").strip()
        after = commit(dir, "feat: after")
        return dir, base, merge, after

    def cloned(self):
        """The history repo as a clone has it: origin/main at main's tip, and origin's default
        branch main."""
        dir, base, merge, after = self.history()
        testkit.git(dir, "update-ref", "refs/remotes/origin/main", after)
        testkit.git(dir, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        return dir, base, merge, after

    def test_finds_a_merge_being_pushed(self):
        dir, base, merge, _ = self.history()
        self.assertEqual(linear_history(dir, push(merge, base)), ["refs/heads/main " + merge[:12]])

    def test_passes_merges_the_remote_has(self):
        dir, _, merge, after = self.history()
        self.assertEqual(linear_history(dir, push(after, merge)), [])

    # A branch new to the remote, or whose remote commit isn't here, is checked against every
    # remote-tracking branch.
    def test_checks_a_new_branch_against_the_remote_tracking_branches(self):
        dir, _, merge, after = self.history()
        for remote in [ZERO, "1" * 40]:
            with self.subTest(remote=remote[:4]):
                self.assertEqual(
                    linear_history(dir, push(after, remote)), ["refs/heads/main " + merge[:12]]
                )
        testkit.git(dir, "update-ref", "refs/remotes/origin/main", merge)
        self.assertEqual(linear_history(dir, push(after, ZERO)), [])

    # A branch rebased onto main sends main's merges past the remote commit, but the remote's
    # default branch already has them.
    def test_passes_a_rebase_onto_mains_merges(self):
        dir, base, _, after = self.cloned()
        testkit.git(dir, "checkout", "-q", "-b", "feature", base)
        old = commit(dir, "feat: feature")
        testkit.git(dir, "checkout", "-q", "-B", "feature", after)
        rebased = commit(dir, "feat: feature")
        self.assertEqual(linear_history(dir, push_feature(rebased, old)), [])

    def test_passes_a_branch_fast_forwarded_onto_main(self):
        dir, base, _, after = self.cloned()
        testkit.git(dir, "checkout", "-q", "-b", "feature", after)
        ahead = commit(dir, "feat: feature")
        self.assertEqual(linear_history(dir, push_feature(ahead, base)), [])

    def test_finds_a_merge_a_rebased_branch_adds(self):
        dir, base, _, after = self.cloned()
        testkit.git(dir, "checkout", "-q", "-b", "old", base)
        old = commit(dir, "feat: feature")
        own = with_merge(dir, "feature", after)
        self.assertEqual(
            linear_history(dir, push_feature(own, old)), ["refs/heads/feature " + own[:12]]
        )

    # A merge on a remote branch other than the default one isn't on the branch the push rewrites.
    def test_finds_a_merge_from_another_remote_branch(self):
        dir, base, _, after = self.cloned()
        other = with_merge(dir, "other", base)
        testkit.git(dir, "update-ref", "refs/remotes/origin/other", other)
        self.assertEqual(linear_history(dir, push(other, after)), ["refs/heads/main " + other[:12]])

    # The tracking ref of the branch pushed to doesn't count, past the remote commit: in CI, where
    # the head is checked as if pushed onto the base, it already has the head.
    def test_finds_a_merge_rewriting_the_default_branch(self):
        dir, base, merge, after = self.cloned()
        testkit.git(dir, "checkout", "-q", "-b", "old", base)
        old = commit(dir, "feat: old")
        self.assertEqual(linear_history(dir, push(after, old)), ["refs/heads/main " + merge[:12]])

    def test_passes_a_linear_history(self):
        dir, base, _, _ = self.history()
        self.assertEqual(linear_history(dir, push(base, ZERO)), [])

    def test_ignores_deletions_and_blank_lines(self):
        dir, base, _, _ = self.history()
        self.assertEqual(linear_history(dir, f"\nrefs/heads/x {ZERO} refs/heads/x {base}\n"), [])

    def test_fails_on_a_commit_not_here(self):
        dir, base, _, _ = self.history()
        with self.assertRaises(Error):
            linear_history(dir, push("2" * 40, base))


if __name__ == "__main__":
    unittest.main()
