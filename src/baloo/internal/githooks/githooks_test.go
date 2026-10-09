package githooks

import (
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

// on turns on the Checks `names`.
func on(names ...string) func(string) bool {
	return func(name string) bool { return slices.Contains(names, name) }
}

var all = on("no-secrets-in-commits", "no-stale-adr-date", "no-ai-coauthor", "conventional-commits",
	"linear-history")

// wantScript is the Git hook `hook` the plugin writes, running the link in `data`.
func wantScript(data, hook string) string {
	return "#!/bin/sh\n" +
		"# managed by baloo: runs the plugin's Checks, rewritten at each session start\n" +
		"b='" + filepath.Join(data, "baloo") + "'\n" +
		`[ ! -x "$b" ] || exec "$b" git-hook ` + hook + ` "$@"` + "\n" +
		`echo "baloo: $b is missing, so the plugin's Checks didn't run" >&2` + "\n"
}

// wantHuskyLine is the line the plugin puts first in husky's `hook`.
func wantHuskyLine(hook string) string {
	return `baloo_hook="$(git rev-parse --git-common-dir)/baloo-hooks/` + hook + `"; ` +
		`[ ! -x "$baloo_hook" ] || "$baloo_hook" "$@" || exit $? # managed by baloo`
}

func read(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(data)
}

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o755); err != nil {
		t.Fatal(err)
	}
}

func missing(t *testing.T, path string) {
	t.Helper()
	if _, err := os.Lstat(path); err == nil {
		t.Errorf("%s is there; want it gone", path)
	}
}

// The plugin writes a Git hook where one of its Checks is on, executable, and leaves the others
// unwritten; once written, writing again changes nothing.
func TestWrite_WritesTheHooksWhoseChecksAreOn(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	r, err := Write(root, data, on("conventional-commits"))
	hooks := filepath.Join(root, ".git", "hooks")
	if err != nil || !reflect.DeepEqual(r, Report{Dir: hooks, Written: []string{"commit-msg"}}) {
		t.Fatalf("Write = %+v, %v; want commit-msg written in %s", r, err, hooks)
	}
	if got, want := read(t, filepath.Join(hooks, "commit-msg")), wantScript(data, "commit-msg"); got != want {
		t.Errorf("commit-msg = %q; want %q", got, want)
	}
	if info, err := os.Stat(filepath.Join(hooks, "commit-msg")); err != nil || info.Mode()&0o111 == 0 {
		t.Errorf("commit-msg's mode = %v, %v; want it executable", info, err)
	}
	missing(t, filepath.Join(hooks, "pre-commit"))
	missing(t, filepath.Join(hooks, "pre-push"))
	if target, err := os.Readlink(filepath.Join(data, "baloo")); err != nil || target == "" {
		t.Errorf("the link in the data folder = %q, %v; want it pointed at the binary", target, err)
	}
	if r, err := Write(root, data, on("conventional-commits")); err != nil || !reflect.DeepEqual(r, Report{Dir: hooks}) {
		t.Errorf("second Write = %+v, %v; want nothing changed", r, err)
	}
}

// A Git hook is written where the Config sets its command, though none of its Checks is on, and
// Inspect names the command among what it runs.
func TestWrite_WritesTheHooksWithACommand(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	r, err := Write(root, data, on("git-hook-commands.pre-commit"))
	hooks := filepath.Join(root, ".git", "hooks")
	if err != nil || !reflect.DeepEqual(r, Report{Dir: hooks, Written: []string{"pre-commit"}}) {
		t.Fatalf("Write = %+v, %v; want pre-commit written in %s", r, err, hooks)
	}
	_, _, got, err := Inspect(root, data, on("no-secrets-in-commits", "git-hook-commands.pre-commit"))
	if err != nil || got[1].State != Running ||
		!reflect.DeepEqual(got[1].Runs, []string{"no-secrets-in-commits", "git-hook-commands.pre-commit"}) {
		t.Errorf("Inspect's pre-commit = %+v, %v; want it running its Check, then its command", got[1], err)
	}
}

// A Git hook whose Checks are all off is taken out, but only the plugin's own.
func TestWrite_TakesOutItsOwn(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	if _, err := Write(root, data, all); err != nil {
		t.Fatal(err)
	}
	hooks := filepath.Join(root, ".git", "hooks")
	r, err := Write(root, data, on("linear-history"))
	if want := (Report{Dir: hooks, Removed: []string{"commit-msg", "pre-commit"}}); err != nil || !reflect.DeepEqual(r, want) {
		t.Errorf("Write with only linear-history = %+v, %v; want %+v", r, err, want)
	}
	missing(t, filepath.Join(hooks, "commit-msg"))
	if got := read(t, filepath.Join(hooks, "pre-push")); got != wantScript(data, "pre-push") {
		t.Errorf("pre-push = %q; want the plugin's", got)
	}
}

// A Git hook the plugin didn't write is left alone, and named with the Checks it keeps from
// running, if any.
func TestWrite_LeavesTheirs(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	theirs := filepath.Join(root, ".git", "hooks", "pre-commit")
	write(t, theirs, "#!/bin/sh\nnpm test\n")
	r, err := Write(root, data, all)
	want := []Blocked{{theirs, []string{"no-secrets-in-commits", "no-stale-adr-date"}}}
	if err != nil || !reflect.DeepEqual(r.Theirs, want) || slices.Contains(r.Written, "pre-commit") {
		t.Errorf("Write = %+v, %v; want pre-commit named as theirs, %+v", r, err, want)
	}
	if got := read(t, theirs); got != "#!/bin/sh\nnpm test\n" {
		t.Errorf("their pre-commit = %q; want it as it was", got)
	}
	if r, err := Write(root, data, on("linear-history")); err != nil || r.Theirs != nil {
		t.Errorf("Write with pre-commit's Checks off = %+v, %v; want theirs not named", r, err)
	}
	if got := read(t, theirs); got != "#!/bin/sh\nnpm test\n" {
		t.Errorf("their pre-commit = %q; want it as it was", got)
	}
}

// Where the Git hooks' folder is in the working tree, each Git hook the plugin writes goes into
// info/exclude.
func TestWrite_ExcludesFromTheWorkingTree(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	testkit.Git(t, root, "config", "core.hooksPath", ".githooks")
	r, err := Write(root, data, on("linear-history"))
	if err != nil || !slices.Equal(r.Written, []string{"pre-push"}) {
		t.Fatalf("Write = %+v, %v; want pre-push written", r, err)
	}
	if got := read(t, filepath.Join(root, ".githooks", "pre-push")); got != wantScript(data, "pre-push") {
		t.Errorf(".githooks/pre-push = %q; want the plugin's", got)
	}
	if got := read(t, filepath.Join(root, ".git", "info", "exclude")); !strings.Contains(got, "\n/.githooks/pre-push\n") {
		t.Errorf("info/exclude = %q; want /.githooks/pre-push in it", got)
	}
}

// With husky 9, the plugin's Git hooks go into the git folder's baloo-hooks/, and a line first in
// husky's own runs each; where a Git hook goes, so does its line, and a file the line was all of.
func TestWrite_Husky(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	write(t, filepath.Join(root, ".husky", "_", "h"), "# husky's\n")
	write(t, filepath.Join(root, ".husky", "pre-commit"), "npm test\n")
	write(t, filepath.Join(root, ".husky", "pre-push"), "#!/usr/bin/env sh\nnpm run lint\n")
	testkit.Git(t, root, "config", "core.hooksPath", ".husky/_")
	r, err := Write(root, data, all)
	ours := filepath.Join(root, ".git", "baloo-hooks")
	want := Report{Dir: ours, Written: []string{"commit-msg", "pre-commit", "pre-push"},
		Husky: []string{".husky/commit-msg", ".husky/pre-commit", ".husky/pre-push"}}
	if err != nil || !reflect.DeepEqual(r, want) {
		t.Fatalf("Write = %+v, %v; want %+v", r, err, want)
	}
	for _, hook := range []string{"commit-msg", "pre-commit", "pre-push"} {
		if got := read(t, filepath.Join(ours, hook)); got != wantScript(data, hook) {
			t.Errorf("baloo-hooks/%s = %q; want the plugin's", hook, got)
		}
		missing(t, filepath.Join(root, ".husky", "_", hook))
	}
	for path, want := range map[string]string{
		"commit-msg": wantHuskyLine("commit-msg") + "\n",
		"pre-commit": wantHuskyLine("pre-commit") + "\nnpm test\n",
		"pre-push":   "#!/usr/bin/env sh\n" + wantHuskyLine("pre-push") + "\nnpm run lint\n",
	} {
		if got := read(t, filepath.Join(root, ".husky", path)); got != want {
			t.Errorf(".husky/%s = %q; want %q", path, got, want)
		}
	}
	if r, err := Write(root, data, all); err != nil || !reflect.DeepEqual(r, Report{Dir: ours}) {
		t.Errorf("second Write = %+v, %v; want nothing changed", r, err)
	}

	r, err = Write(root, data, on())
	want = Report{Dir: ours, Removed: []string{"commit-msg", "pre-commit", "pre-push"},
		Husky: []string{".husky/commit-msg", ".husky/pre-commit", ".husky/pre-push"}}
	if err != nil || !reflect.DeepEqual(r, want) {
		t.Fatalf("Write with every Check off = %+v, %v; want %+v", r, err, want)
	}
	missing(t, filepath.Join(root, ".husky", "commit-msg"))
	if got := read(t, filepath.Join(root, ".husky", "pre-commit")); got != "npm test\n" {
		t.Errorf(".husky/pre-commit = %q; want it as it was", got)
	}
	if got := read(t, filepath.Join(root, ".husky", "pre-push")); got != "#!/usr/bin/env sh\nnpm run lint\n" {
		t.Errorf(".husky/pre-push = %q; want it as it was", got)
	}
}

// states are the State of each Git hook in `hooks`, by name.
func states(hooks []Hook) map[string]State {
	got := map[string]State{}
	for _, h := range hooks {
		got[h.Name] = h.State
	}
	return got
}

// Inspect finds each Git hook as it is against what Write would make of it, and changes nothing.
func TestInspect(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	hooks := filepath.Join(root, ".git", "hooks")
	dir, husky, got, err := Inspect(root, data, all)
	want := map[string]State{"commit-msg": Missing, "pre-commit": Missing, "pre-push": Missing}
	if err != nil || dir != hooks || husky || !reflect.DeepEqual(states(got), want) {
		t.Fatalf("Inspect before Write = %q, %v, %v, %v; want %v in %s", dir, husky, states(got), err, want, hooks)
	}
	missing(t, filepath.Join(hooks, "commit-msg"))

	if _, err := Write(root, data, all); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(hooks, "pre-commit"), "#!/bin/sh\nnpm test\n")
	write(t, filepath.Join(hooks, "pre-push"), wantScript(t.TempDir(), "pre-push"))
	_, _, got, err = Inspect(root, data, all)
	want = map[string]State{"commit-msg": Running, "pre-commit": Theirs, "pre-push": Outdated}
	if err != nil || !reflect.DeepEqual(states(got), want) {
		t.Errorf("Inspect = %v, %v; want %v", states(got), err, want)
	}
	if got[0].Bin != filepath.Join(data, "baloo") || got[1].Bin != "" ||
		!reflect.DeepEqual(got[0].Runs, []string{"no-ai-coauthor", "conventional-commits"}) {
		t.Errorf("Inspect = %+v; want commit-msg running the link in %s, and pre-commit no binary", got, data)
	}

	_, _, got, err = Inspect(root, data, on())
	want = map[string]State{"commit-msg": Leftover, "pre-commit": Off, "pre-push": Leftover}
	if err != nil || !reflect.DeepEqual(states(got), want) {
		t.Errorf("Inspect with every Check off = %v, %v; want %v", states(got), err, want)
	}
}

// With husky 9, Inspect finds the plugin's Git hooks in the git folder, and a line in husky's own
// that isn't as session start keeps it.
func TestInspect_Husky(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	write(t, filepath.Join(root, ".husky", "_", "h"), "# husky's\n")
	testkit.Git(t, root, "config", "core.hooksPath", ".husky/_")
	if _, err := Write(root, data, all); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(root, ".husky", "pre-push"), "npm run lint\n")
	dir, husky, got, err := Inspect(root, data, all)
	if err != nil || dir != filepath.Join(root, ".git", "baloo-hooks") || !husky {
		t.Fatalf("Inspect = %q, %v, %v; want husky's, in .git/baloo-hooks", dir, husky, err)
	}
	for _, h := range got {
		if h.State != Running || h.HuskyOutdated != (h.Name == "pre-push") {
			t.Errorf("Inspect's %s = %+v; want it running, and only pre-push's husky line outdated", h.Name, h)
		}
	}
}
