package condense

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

// Claude Code keeps a project's Transcripts in projects/ under its config folder, in a folder
// named after the project's path with each character but a letter or digit as `-`.
func TestDir_FindsTheProjectsTranscriptsFromItOrAFolderInIt(t *testing.T) {
	config := t.TempDir()
	want := filepath.Join(config, "projects", "-home-me-my-repo-v2")
	if err := os.MkdirAll(want, 0o755); err != nil {
		t.Fatal(err)
	}
	for _, cwd := range []string{"/home/me/my_repo.v2", "/home/me/my_repo.v2/src/x"} {
		if got := Dir(config, cwd); got != want {
			t.Errorf("Dir(%q) = %q, want %q", cwd, got, want)
		}
	}
	if got := Dir(config, "/home/me/other"); got != "" {
		t.Errorf("Dir of a project without Transcripts = %q, want none", got)
	}
}

// write writes the Transcript `text` as the session `id` in `dir`, last changed `ago` before now.
func write(t *testing.T, dir, id string, text []byte, ago time.Duration) {
	t.Helper()
	path := filepath.Join(dir, id+".jsonl")
	if err := os.WriteFile(path, text, 0o644); err != nil {
		t.Fatal(err)
	}
	when := time.Now().Add(-ago)
	if err := os.Chtimes(path, when, when); err != nil {
		t.Fatal(err)
	}
}

func TestLatest_TakesTheNewestSessionsWorthARetro(t *testing.T) {
	dir := t.TempDir()
	headless := `{"type":"user","entrypoint":"sdk-cli","message":{"content":"review the session"}}`
	clear := `{"type":"user","message":{"content":"<command-name>/clear</command-name>\n<command-args></command-args>"}}`
	write(t, dir, "old", transcript(start), 3*time.Hour)
	write(t, dir, "older", transcript(start), 4*time.Hour)
	write(t, dir, "new", transcript(start), time.Hour)
	write(t, dir, "headless", transcript(headless), 0)
	write(t, dir, "cleared", transcript(clear), 0)
	if err := os.Mkdir(filepath.Join(dir, "new"), 0o755); err != nil { // a session's subagents
		t.Fatal(err)
	}
	sessions, err := Latest(dir, 2)
	if err != nil {
		t.Fatal(err)
	}
	var got []string
	for _, s := range sessions {
		got = append(got, s.ID)
	}
	if len(got) != 2 || got[0] != "new" || got[1] != "old" {
		t.Errorf("Latest(2) = %q, want [new old]", got)
	}
}
