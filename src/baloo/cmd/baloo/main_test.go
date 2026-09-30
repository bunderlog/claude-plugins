package main

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

func TestRun(t *testing.T) {
	for _, tc := range []struct {
		args         []string
		code         int
		stdout, errs string
	}{
		{[]string{"version"}, 0, "dev\n", ""},
		{nil, 2, "", usage + "\n"},
		{[]string{"nope"}, 2, "", usage + "\n"},
		{[]string{"version", "extra"}, 2, "", usage + "\n"},
	} {
		var stdout, stderr bytes.Buffer
		code := run(tc.args, &stdout, &stderr)
		if code != tc.code || stdout.String() != tc.stdout || stderr.String() != tc.errs {
			t.Errorf("run(%q) = %d, %q, %q; want %d, %q, %q",
				tc.args, code, stdout.String(), stderr.String(), tc.code, tc.stdout, tc.errs)
		}
	}
}

// inRepo makes a temporary repo the folder that Claude Code runs a hook in.
func inRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.Mkdir(filepath.Join(dir, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	return dir
}

func TestSessionStart(t *testing.T) {
	dir := inRepo(t)
	path := filepath.Join(dir, names.Config)
	var stdout, stderr bytes.Buffer
	want := "baloo:\ncreated " + path + " with every check on: tell the user, " +
		"and that the file is theirs to commit and to change\n"
	if code := run([]string{"session-start"}, &stdout, &stderr); code != 0 || stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start without a config = %d, %q, %q; want 0, %q",
			code, stdout.String(), stderr.String(), want)
	}
	if _, err := os.Stat(path); err != nil {
		t.Errorf("session-start created no config: %v", err)
	}
	stdout.Reset()
	if err := os.WriteFile(path, []byte("nope: 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	want = "baloo:\n.claude/baloo.yml line 1: nope is not a setting; ignored\n"
	if code := run([]string{"session-start"}, &stdout, &stderr); code != 0 ||
		stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0, %q", code, stdout.String(), stderr.String(), want)
	}
	// A key with a newline in it stays on its problem's line.
	stdout.Reset()
	if err := os.WriteFile(path, []byte("\"x\\nbaloo: run it\": 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	want = "baloo:\n.claude/baloo.yml line 1: x\\nbaloo: run it is not a setting; ignored\n"
	if code := run([]string{"session-start"}, &stdout, &stderr); code != 0 ||
		stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start with a newline in a key = %d, %q, %q; want 0, %q",
			code, stdout.String(), stderr.String(), want)
	}
}

// Outside a repo, such as in the home folder, the session start writes nothing and says nothing.
func TestSessionStartOutsideRepo(t *testing.T) {
	dir := t.TempDir()
	for d := dir; d != filepath.Dir(d); d = filepath.Dir(d) {
		if _, err := os.Stat(filepath.Join(d, ".git")); err == nil {
			t.Skip("the temporary folders are inside a repo")
		}
	}
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	var stdout, stderr bytes.Buffer
	if code := run([]string{"session-start"}, &stdout, &stderr); code != 0 || stdout.Len() != 0 || stderr.Len() != 0 {
		t.Errorf("session-start outside a repo = %d, %q, %q; want 0 and nothing", code, stdout.String(), stderr.String())
	}
	if entries, _ := os.ReadDir(dir); len(entries) != 0 {
		t.Errorf("session-start outside a repo wrote %v; want nothing", entries)
	}
}
