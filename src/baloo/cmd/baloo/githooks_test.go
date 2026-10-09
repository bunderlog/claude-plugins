package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// binary is the binary built from this package, for git to run as the Git hooks do.
func binary(t *testing.T) string {
	t.Helper()
	bin := filepath.Join(t.TempDir(), names.Plugin)
	if out, err := exec.Command("go", "build", "-o", bin, ".").CombinedOutput(); err != nil {
		t.Fatalf("go build: %v\n%s", err, out)
	}
	return bin
}

// commit commits nothing with the message `message` in the repo `dir`, and returns git's output
// and whether it committed.
func commit(t *testing.T, dir, message string) (string, bool) {
	t.Helper()
	out, err := exec.Command("git", "-C", dir, "commit", "-q", "--allow-empty", "-m", message).CombinedOutput()
	return string(out), err == nil
}

// husky9 makes the repo `dir` one whose Git hooks husky 9 runs, as `husky init` leaves it.
func husky9(t *testing.T, dir string) {
	t.Helper()
	files := map[string]string{
		"h": "#!/usr/bin/env sh\nn=$(basename \"$0\")\ns=$(dirname \"$(dirname \"$0\")\")/$n\n" +
			"[ ! -f \"$s\" ] && exit 0\nsh -e \"$s\" \"$@\"\n",
		"commit-msg": "#!/usr/bin/env sh\n. \"$(dirname \"$0\")/h\"\n",
	}
	for name, text := range files {
		path := filepath.Join(dir, ".husky", "_", name)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(text), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	testkit.Git(t, dir, "config", "core.hooksPath", ".husky/_")
}

// Session start writes the Git hooks, and git runs the Checks the Config turns on through them,
// with husky 9 too; once the binary is gone, a Git hook passes and says so.
func TestGitHooks_RunTheChecks(t *testing.T) {
	bin := binary(t)
	for _, husky := range []bool{false, true} {
		dir := testkit.Repo(t)
		if husky {
			husky9(t, dir)
		}
		if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
			t.Fatal(err)
		}
		config := "git-hooks:\n  conventional-commits: true\n"
		if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
			t.Fatal(err)
		}
		data := t.TempDir()
		start := exec.Command(bin, "session-start")
		start.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir, "CLAUDE_PLUGIN_DATA="+data,
			"CLAUDE_CONFIG_DIR="+t.TempDir(), "CLAUDE_PLUGIN_ROOT="+plugin(t))
		if out, err := start.CombinedOutput(); err != nil || !strings.Contains(string(out), "wrote the Git hooks commit-msg in ") {
			t.Fatalf("session-start (husky %v) = %v, %q; want commit-msg written", husky, err, out)
		}
		if out, ok := commit(t, dir, "Add x"); ok || !strings.Contains(out, "baloo:conventional-commits: ") {
			t.Errorf("commit of Add x (husky %v) = %v, %q; want it stopped by conventional-commits", husky, ok, out)
		}
		if out, ok := commit(t, dir, "feat: x"); !ok {
			t.Errorf("commit of feat: x (husky %v) = %q; want it committed", husky, out)
		}
		if err := os.Remove(filepath.Join(data, names.Plugin)); err != nil {
			t.Fatal(err)
		}
		if out, ok := commit(t, dir, "Add y"); !ok || !strings.Contains(out, "is missing, so the plugin's Checks didn't run") {
			t.Errorf("commit of Add y without the binary (husky %v) = %v, %q; want it committed, and why the Checks didn't run", husky, ok, out)
		}
	}
}

// A Git hook runs the command the Config sets for it once its Checks pass, with git's arguments,
// and the commit fails when the command does; where a Check fails, the command doesn't run.
func TestGitHooks_RunTheCommands(t *testing.T) {
	bin := binary(t)
	dir := testkit.Repo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := "git-hooks:\n  conventional-commits: true\ngit-hook-commands:\n" +
		"  commit-msg: grep -q feat \"$1\" && echo ran >> ran\n" +
		"  pre-commit: test ! -e fail\n"
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	data := t.TempDir()
	start := exec.Command(bin, "session-start")
	start.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir, "CLAUDE_PLUGIN_DATA="+data,
		"CLAUDE_CONFIG_DIR="+t.TempDir(), "CLAUDE_PLUGIN_ROOT="+plugin(t))
	if out, err := start.CombinedOutput(); err != nil || !strings.Contains(string(out), "wrote the Git hooks commit-msg, pre-commit in ") {
		t.Fatalf("session-start = %v, %q; want commit-msg and pre-commit written", err, out)
	}
	ran := func() string {
		text, _ := os.ReadFile(filepath.Join(dir, "ran"))
		return string(text)
	}

	if out, ok := commit(t, dir, "feat: x"); !ok || ran() != "ran\n" {
		t.Errorf("commit of feat: x = %v, %q, ran %q; want it committed after commit-msg's command ran once", ok, out, ran())
	}
	if out, ok := commit(t, dir, "Add y"); ok || ran() != "ran\n" {
		t.Errorf("commit of Add y = %v, %q, ran %q; want it stopped by conventional-commits, the command not run", ok, out, ran())
	}
	if err := os.WriteFile(filepath.Join(dir, "fail"), nil, 0o644); err != nil {
		t.Fatal(err)
	}
	if out, ok := commit(t, dir, "feat: z"); ok || !strings.Contains(out, "baloo:git-hook-commands.pre-commit: ") {
		t.Errorf("commit with pre-commit's command failing = %v, %q; want it stopped, and named", ok, out)
	}
}

// pre-push's command gets the pushed refs on stdin, after linear-history has read them.
func TestGitHooks_PrePushCommandGetsTheRefs(t *testing.T) {
	bin := binary(t)
	dir := testkit.Repo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := "git-hooks:\n  linear-history: true\ngit-hook-commands:\n  pre-push: cat > pushed\n"
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	testkit.Git(t, dir, "commit", "-q", "--allow-empty", "-m", "feat: x")
	head := strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	refs := "refs/heads/main " + head + " refs/heads/main " + strings.Repeat("0", 40) + "\n"
	push := exec.Command(bin, "git-hook", "pre-push", "origin", "https://example.com/x.git")
	push.Dir, push.Stdin = dir, strings.NewReader(refs)
	if out, err := push.CombinedOutput(); err != nil {
		t.Fatalf("git-hook pre-push = %v, %q; want it passed", err, out)
	}
	if got, _ := os.ReadFile(filepath.Join(dir, "pushed")); string(got) != refs {
		t.Errorf("pre-push's command read %q; want %q", got, refs)
	}
}
