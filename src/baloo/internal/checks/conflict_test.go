package checks

import (
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

func noConflictMarkers(t *testing.T, dir string) []string {
	t.Helper()
	found, err := NoConflictMarkers(dir)
	if err != nil {
		t.Fatalf("NoConflictMarkers: %v", err)
	}
	return found
}

func TestNoConflictMarkers_FindsEachMarkerTheStagedChangesAdd(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a.go": "a\n<<<<<<< HEAD\nx \n=======\ny\n>>>>>>> topic\n"})
	want := []string{"a.go:2", "a.go:4", "a.go:6"}
	if got := noConflictMarkers(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoConflictMarkers = %q, want %q", got, want)
	}
}

func TestNoConflictMarkers_PassesWhatIsNotAMarker(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{
		"a.md":  "Title\n=======\n\ntrailing space \n",
		"b.txt": "<<<<<<<< eight, not seven\n",
	})
	if got := noConflictMarkers(t, dir); got != nil {
		t.Errorf("NoConflictMarkers = %q, want none", got)
	}
}

// A file that holds markers on purpose passes with a longer conflict-marker-size in
// .gitattributes, as git's own check reads it.
func TestNoConflictMarkers_PassesAFileWithALongerMarkerSize(t *testing.T) {
	dir := testkit.Repo(t)
	if err := os.WriteFile(filepath.Join(dir, ".gitattributes"),
		[]byte("testdata/* conflict-marker-size=32\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	stage(t, dir, map[string]string{"testdata/merge.txt": "<<<<<<< ours\n"})
	if got := noConflictMarkers(t, dir); got != nil {
		t.Errorf("NoConflictMarkers = %q, want none", got)
	}
}

func TestNoConflictMarkers_PassesNothingStaged(t *testing.T) {
	if got := noConflictMarkers(t, testkit.Repo(t)); got != nil {
		t.Errorf("NoConflictMarkers = %q, want none", got)
	}
}

func TestNoConflictMarkers_FailsOutsideARepo(t *testing.T) {
	if _, err := NoConflictMarkers(t.TempDir()); err == nil {
		t.Error("NoConflictMarkers outside a repo = no error, want one")
	}
}
