package main

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// doctorRun runs doctor and returns its exit code and what it printed, failing the test when it
// writes to stderr.
func doctorRun(t *testing.T) (int, string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	code := run([]string{"doctor"}, nil, &stdout, &stderr)
	if stderr.Len() != 0 {
		t.Errorf("doctor wrote %q to stderr; want nothing", stderr.String())
	}
	return code, stdout.String()
}

// contains fails the test unless `out` holds each of `want`.
func contains(t *testing.T, out string, want ...string) {
	t.Helper()
	for _, w := range want {
		if !strings.Contains(out, w) {
			t.Errorf("doctor printed %q; want it to hold %q", out, w)
		}
	}
}

// After session start, doctor finds no problem and shows what is on, and why.
func TestDoctor(t *testing.T) {
	dir := inRepo(t)
	var stdout, stderr bytes.Buffer
	if code := start(t, &stdout, &stderr); code != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	code, out := doctorRun(t)
	if code != 0 {
		t.Errorf("doctor = %d; want 0", code)
	}
	contains(t, out,
		"baloo dev doctor in "+dir+"\n\nNo problems.\n",
		"Config: "+filepath.Join(dir, names.Config)+"\n",
		"no-secrets-in-context  on\n",
		"commit-msg  running: no-ai-coauthor, conventional-commits\n",
		"Guidelines:\n")
}

// doctor names each problem, first, with what fixes it, and fails; it changes nothing.
func TestDoctor_Problems(t *testing.T) {
	dir := inRepo(t)
	var stdout, stderr bytes.Buffer
	if code := start(t, &stdout, &stderr); code != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	config := filepath.Join(dir, names.Config)
	text, err := os.ReadFile(config)
	if err != nil {
		t.Fatal(err)
	}
	text = append(text, "nope: 1\nstop-check: make\nclaude-hooks:\n  no-git-hook-bypass: false\n"...)
	theirs := filepath.Join(dir, ".git", "hooks", "pre-commit")
	link := filepath.Join(os.Getenv("CLAUDE_PLUGIN_DATA"), names.Plugin)
	for path, data := range map[string]string{config: string(text), theirs: "#!/bin/sh\nnpm test\n"} {
		if err := os.WriteFile(path, []byte(data), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.Remove(link); err != nil {
		t.Fatal(err)
	}
	code, out := doctorRun(t)
	if code != 1 {
		t.Errorf("doctor = %d; want 1", code)
	}
	contains(t, out,
		"\nProblems:\n- ",
		"- "+link+" is missing, so the Git hooks and the Status line run nothing",
		"- "+theirs+" is not the plugin's Git hook, so no-secrets-in-commits, no-stale-adr-date, no-conflict-markers, no-large-files don't run",
		"nope is not a setting; ignored\n",
		"stop-check is no longer a setting and is ignored: delete it\n",
		"no-git-hook-bypass     off\n",
		"pre-commit  theirs: no-secrets-in-commits, no-stale-adr-date, no-conflict-markers, no-large-files\n")
	if _, err := os.Lstat(link); err == nil {
		t.Errorf("doctor put back %s; want it to change nothing", link)
	}
}

// Outside a repo, doctor says no Config is read, and shows the Checks a Hook runs on by default.
func TestDoctor_OutsideRepo(t *testing.T) {
	dir := t.TempDir()
	for d := dir; d != filepath.Dir(d); d = filepath.Dir(d) {
		if _, err := os.Stat(filepath.Join(d, ".git")); err == nil {
			t.Skip("the temporary folders are inside a repo")
		}
	}
	inRepo(t)
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	_, out := doctorRun(t)
	contains(t, out, "Config: none, outside a repo", "no-secrets-in-context  on, by default\n",
		"linear-history         off, by default\n")
	if strings.Contains(out, "Git hooks in ") {
		t.Errorf("doctor outside a repo printed %q; want no Git hooks", out)
	}
}
