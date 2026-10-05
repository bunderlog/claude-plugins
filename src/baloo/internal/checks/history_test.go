package checks

import (
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

var zero = strings.Repeat("0", 40)

// commit makes an empty commit in the repo `dir` and returns it.
func commit(t *testing.T, dir, message string) string {
	t.Helper()
	testkit.Git(t, dir, "commit", "-q", "--allow-empty", "-m", message)
	return strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
}

// history is a repo whose main has a merge commit, with the commits before it, of it and after it.
func history(t *testing.T) (dir, base, merge, after string) {
	t.Helper()
	dir = testkit.Repo(t)
	base = commit(t, dir, "feat: base")
	testkit.Git(t, dir, "checkout", "-q", "-b", "side")
	commit(t, dir, "feat: side")
	testkit.Git(t, dir, "checkout", "-q", "main")
	commit(t, dir, "feat: main")
	testkit.Git(t, dir, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
	merge = strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	after = commit(t, dir, "feat: after")
	return dir, base, merge, after
}

// cloned is the history repo as a clone has it: origin/main at main's tip, and origin's default
// branch main.
func cloned(t *testing.T) (dir, base, merge, after string) {
	t.Helper()
	dir, base, merge, after = history(t)
	testkit.Git(t, dir, "update-ref", "refs/remotes/origin/main", after)
	testkit.Git(t, dir, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
	return dir, base, merge, after
}

// withMerge makes a branch `branch` from `from` with a merge commit of its own, and returns the merge.
func withMerge(t *testing.T, dir, branch, from string) string {
	t.Helper()
	testkit.Git(t, dir, "checkout", "-q", "-b", branch, from)
	testkit.Git(t, dir, "checkout", "-q", "-b", branch+"-topic")
	commit(t, dir, "feat: topic")
	testkit.Git(t, dir, "checkout", "-q", branch)
	testkit.Git(t, dir, "merge", "-q", "--no-ff", "-m", "Merge topic", branch+"-topic")
	return strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
}

// push is the line git gives pre-push for pushing `local` to main, where the remote had `remote`.
func push(local, remote string) string {
	return "refs/heads/main " + local + " refs/heads/main " + remote + "\n"
}

// pushFeature is the line git gives pre-push for pushing `local` to feature, where the remote had
// `remote`.
func pushFeature(local, remote string) string {
	return "refs/heads/feature " + local + " refs/heads/feature " + remote + "\n"
}

func linearHistory(t *testing.T, dir, pushed string) []string {
	t.Helper()
	found, err := LinearHistory(dir, pushed)
	if err != nil {
		t.Fatalf("LinearHistory: %v", err)
	}
	return found
}

func TestLinearHistory_FindsAMergeBeingPushed(t *testing.T) {
	dir, base, merge, _ := history(t)
	want := []string{"refs/heads/main " + merge[:12]}
	if got := linearHistory(t, dir, push(merge, base)); !slices.Equal(got, want) {
		t.Errorf("LinearHistory = %q, want %q", got, want)
	}
}

func TestLinearHistory_PassesMergesTheRemoteHas(t *testing.T) {
	dir, _, merge, after := history(t)
	if got := linearHistory(t, dir, push(after, merge)); got != nil {
		t.Errorf("LinearHistory = %q, want none", got)
	}
}

// A branch new to the remote, or whose remote commit isn't here, is checked against every
// remote-tracking branch.
func TestLinearHistory_ChecksANewBranchAgainstTheRemoteTrackingBranches(t *testing.T) {
	dir, _, merge, after := history(t)
	want := []string{"refs/heads/main " + merge[:12]}
	for _, remote := range []string{zero, strings.Repeat("1", 40)} {
		if got := linearHistory(t, dir, push(after, remote)); !slices.Equal(got, want) {
			t.Errorf("LinearHistory where the remote had %s = %q, want %q", remote[:4], got, want)
		}
	}
	testkit.Git(t, dir, "update-ref", "refs/remotes/origin/main", merge)
	if got := linearHistory(t, dir, push(after, zero)); got != nil {
		t.Errorf("LinearHistory with the merge on origin/main = %q, want none", got)
	}
}

// A branch rebased onto main sends main's merges past the remote commit, but the remote's default
// branch already has them.
func TestLinearHistory_PassesARebaseOntoMainsMerges(t *testing.T) {
	dir, base, _, after := cloned(t)
	testkit.Git(t, dir, "checkout", "-q", "-b", "feature", base)
	old := commit(t, dir, "feat: feature")
	testkit.Git(t, dir, "checkout", "-q", "-B", "feature", after)
	rebased := commit(t, dir, "feat: feature")
	if got := linearHistory(t, dir, pushFeature(rebased, old)); got != nil {
		t.Errorf("LinearHistory = %q, want none", got)
	}
}

func TestLinearHistory_PassesABranchFastForwardedOntoMain(t *testing.T) {
	dir, base, _, after := cloned(t)
	testkit.Git(t, dir, "checkout", "-q", "-b", "feature", after)
	ahead := commit(t, dir, "feat: feature")
	if got := linearHistory(t, dir, pushFeature(ahead, base)); got != nil {
		t.Errorf("LinearHistory = %q, want none", got)
	}
}

func TestLinearHistory_FindsAMergeARebasedBranchAdds(t *testing.T) {
	dir, base, _, after := cloned(t)
	testkit.Git(t, dir, "checkout", "-q", "-b", "old", base)
	old := commit(t, dir, "feat: feature")
	own := withMerge(t, dir, "feature", after)
	want := []string{"refs/heads/feature " + own[:12]}
	if got := linearHistory(t, dir, pushFeature(own, old)); !slices.Equal(got, want) {
		t.Errorf("LinearHistory = %q, want %q", got, want)
	}
}

// A merge on a remote branch other than the default one isn't on the branch the push rewrites.
func TestLinearHistory_FindsAMergeFromAnotherRemoteBranch(t *testing.T) {
	dir, base, _, after := cloned(t)
	other := withMerge(t, dir, "other", base)
	testkit.Git(t, dir, "update-ref", "refs/remotes/origin/other", other)
	want := []string{"refs/heads/main " + other[:12]}
	if got := linearHistory(t, dir, push(other, after)); !slices.Equal(got, want) {
		t.Errorf("LinearHistory = %q, want %q", got, want)
	}
}

// The tracking ref of the branch pushed to doesn't count, past the remote commit: in CI, where the
// head is checked as if pushed onto the base, it already has the head.
func TestLinearHistory_FindsAMergeRewritingTheDefaultBranch(t *testing.T) {
	dir, base, merge, after := cloned(t)
	testkit.Git(t, dir, "checkout", "-q", "-b", "old", base)
	old := commit(t, dir, "feat: old")
	want := []string{"refs/heads/main " + merge[:12]}
	if got := linearHistory(t, dir, push(after, old)); !slices.Equal(got, want) {
		t.Errorf("LinearHistory = %q, want %q", got, want)
	}
}

func TestLinearHistory_PassesALinearHistory(t *testing.T) {
	dir, base, _, _ := history(t)
	if got := linearHistory(t, dir, push(base, zero)); got != nil {
		t.Errorf("LinearHistory = %q, want none", got)
	}
}

func TestLinearHistory_IgnoresDeletionsAndBlankLines(t *testing.T) {
	dir, base, _, _ := history(t)
	if got := linearHistory(t, dir, "\nrefs/heads/x "+zero+" refs/heads/x "+base+"\n"); got != nil {
		t.Errorf("LinearHistory = %q, want none", got)
	}
}

func TestLinearHistory_FailsOnACommitNotHere(t *testing.T) {
	dir, base, _, _ := history(t)
	if _, err := LinearHistory(dir, push(strings.Repeat("2", 40), base)); err == nil {
		t.Error("LinearHistory pushing a commit not in the repo = no error, want one")
	}
}
