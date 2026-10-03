package checks

import (
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

func noLargeFiles(t *testing.T, dir string, maxKB int) []string {
	t.Helper()
	found, err := NoLargeFiles(dir, maxKB)
	if err != nil {
		t.Fatalf("NoLargeFiles: %v", err)
	}
	return found
}

func TestNoLargeFiles_FindsAnAddedFileOverTheLimit(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{
		"bin/app":  strings.Repeat("x", 3*1024+1),
		"small.go": strings.Repeat("x", 3*1024),
	})
	want := []string{"bin/app: 4 KB, over 3 KB"}
	if got := noLargeFiles(t, dir, 3); !slices.Equal(got, want) {
		t.Errorf("NoLargeFiles = %q, want %q", got, want)
	}
}

// Without a limit of its own, a file may be 1 MB.
func TestNoLargeFiles_LimitsAFileTo1MBByDefault(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a": strings.Repeat("x", 1024*1024)})
	if got := noLargeFiles(t, dir, 0); got != nil {
		t.Errorf("NoLargeFiles of 1 MB = %q, want none", got)
	}
	stage(t, dir, map[string]string{"b": strings.Repeat("x", 1024*1024+1)})
	want := []string{"b: 1025 KB, over 1024 KB"}
	if got := noLargeFiles(t, dir, 0); !slices.Equal(got, want) {
		t.Errorf("NoLargeFiles = %q, want %q", got, want)
	}
}

// A file already committed passes when it changes or moves: it was let in once.
func TestNoLargeFiles_PassesAFileAlreadyCommitted(t *testing.T) {
	dir := testkit.Repo(t)
	big := strings.Repeat("x", 4*1024)
	stage(t, dir, map[string]string{"data.bin": big})
	testkit.Git(t, dir, "commit", "-q", "-m", "chore: data")
	stage(t, dir, map[string]string{"data.bin": big + "y"})
	testkit.Git(t, dir, "mv", "data.bin", "moved.bin")
	if got := noLargeFiles(t, dir, 1); got != nil {
		t.Errorf("NoLargeFiles = %q, want none", got)
	}
}

func TestNoLargeFiles_FailsOutsideARepo(t *testing.T) {
	if _, err := NoLargeFiles(t.TempDir(), 0); err == nil {
		t.Error("NoLargeFiles outside a repo = no error, want one")
	}
}
