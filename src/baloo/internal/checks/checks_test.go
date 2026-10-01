package checks

import (
	"maps"
	"slices"
	"testing"
)

// Each Check a Git hook runs belongs to one Git hook the plugin writes.
func TestGitHooks(t *testing.T) {
	var got []string
	for _, hook := range slices.Sorted(maps.Keys(GitHooks)) {
		got = append(got, GitHooks[hook]...)
	}
	slices.Sort(got)
	if want := slices.Sorted(slices.Values(GitHookChecks)); !slices.Equal(got, want) {
		t.Errorf("the Git hooks' checks = %q; want each of %q once", got, want)
	}
}
