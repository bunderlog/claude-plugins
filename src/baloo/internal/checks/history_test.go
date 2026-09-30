package checks

import (
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

var zero = strings.Repeat("0", 40)

// history is a repo whose main has a merge commit, with the commits before it, of it and after it.
func history(t *testing.T) (dir, base, merge, after string) {
	t.Helper()
	dir = testkit.Repo(t)
	commit := func(message string) string {
		testkit.Git(t, dir, "commit", "-q", "--allow-empty", "-m", message)
		return strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	}
	base = commit("feat: base")
	testkit.Git(t, dir, "checkout", "-q", "-b", "side")
	commit("feat: side")
	testkit.Git(t, dir, "checkout", "-q", "main")
	commit("feat: main")
	testkit.Git(t, dir, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
	merge = strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	after = commit("feat: after")
	return dir, base, merge, after
}

// push is the line git gives pre-push for pushing `local` to main, where the remote had `remote`.
func push(local, remote string) string {
	return "refs/heads/main " + local + " refs/heads/main " + remote + "\n"
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
