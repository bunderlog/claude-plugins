package checks

import (
	"bytes"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

// all turns every Check on.
func all(string) bool { return true }

// message is a commit message file holding `text`.
func message(t *testing.T, text string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "COMMIT_EDITMSG")
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

// run is Run's exit code and what it printed.
func run(t *testing.T, name string, args []string, in Input) (int, string) {
	t.Helper()
	var stderr bytes.Buffer
	code, ok := Run(name, args, in, all, &stderr)
	if !ok {
		t.Fatalf("Run(%s, %q) not ok", name, args)
	}
	return code, stderr.String()
}

// A commit-msg Check fails with what is wrong, for git to stop the commit and show it.
func TestRun_CommitMessage(t *testing.T) {
	for _, tc := range []struct {
		name, message string
		code          int
		errs          string
	}{
		{"no-ai-coauthor", "feat: x\n\nCo-authored-by: Jane Doe <jane@example.com>\n", 0, ""},
		{"no-ai-coauthor", "feat: x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", 1,
			"baloo:no-ai-coauthor: remove the AI co-author or credit:\n" +
				"Co-Authored-By: Claude <noreply@anthropic.com>\n"},
		{"conventional-commits", "feat: x\n", 0, ""},
		{"conventional-commits", "Add x\n", 1,
			"baloo:conventional-commits: \"Add x\" is not `type(scope): description`\n"},
	} {
		code, errs := run(t, tc.name, []string{message(t, tc.message)}, Input{})
		if code != tc.code || errs != tc.errs {
			t.Errorf("%s on %q = %d, %q; want %d, %q", tc.name, tc.message, code, errs, tc.code, tc.errs)
		}
	}
	missing := filepath.Join(t.TempDir(), "nope")
	for _, name := range []string{"no-ai-coauthor", "conventional-commits"} {
		if code, errs := run(t, name, []string{missing}, Input{}); code != 2 ||
			!strings.HasPrefix(errs, "baloo:"+name+": ") {
			t.Errorf("%s on a missing file = %d, %q; want 2 and why", name, code, errs)
		}
	}
}

// conventional-commits takes its settings from the Input.
func TestRun_CommitRules(t *testing.T) {
	path := message(t, "wip: x\n")
	for _, tc := range []struct {
		rules CommitRules
		code  int
	}{{CommitRules{}, 1}, {CommitRules{Types: []string{"wip"}}, 0}, {CommitRules{AnyType: true}, 0}} {
		if code, errs := run(t, "conventional-commits", []string{path}, Input{Rules: tc.rules}); code != tc.code {
			t.Errorf("conventional-commits of wip: x with %+v = %d, %q; want %d", tc.rules, code, errs, tc.code)
		}
	}
}

// The pre-commit Check no-secrets-in-commits fails with where each Secret is, but not the Secret.
func TestRun_NoSecretsInCommits(t *testing.T) {
	dir := testkit.Repo(t)
	if code, errs := run(t, "no-secrets-in-commits", nil, Input{Dir: dir}); code != 0 || errs != "" {
		t.Errorf("no-secrets-in-commits with nothing staged = %d, %q; want 0", code, errs)
	}
	secret := "AKIA" + "IOSFODNN7EXAMPLE" // cspell:disable-line
	if err := os.WriteFile(filepath.Join(dir, "a.go"), []byte(secret), 0o644); err != nil {
		t.Fatal(err)
	}
	testkit.Git(t, dir, "add", "a.go")
	want := "baloo:no-secrets-in-commits: remove each secret, or mark a false alarm with baloo:allow-secret:\n" +
		"a.go:1: an AWS access key\n"
	if code, errs := run(t, "no-secrets-in-commits", nil, Input{Dir: dir}); code != 1 || errs != want {
		t.Errorf("no-secrets-in-commits with a secret staged = %d, %q; want 1, %q", code, errs, want)
	}
}

// The pre-commit Check no-stale-adr-date fails with each ADR changed without today's Date.
func TestRun_NoStaleADRDate(t *testing.T) {
	dir := testkit.Repo(t)
	path := filepath.Join(dir, ".about", "adr", "billing.md")
	write := func(date, decision string) {
		t.Helper()
		if err := os.WriteFile(path, []byte("# Billing\n\nDate: "+date+"\n\n"+decision+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		testkit.Git(t, dir, "add", path)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	write("2020-01-01", "Invoices are monthly.")
	testkit.Git(t, dir, "commit", "-q", "-m", "docs: adr")
	write("2020-01-01", "Invoices are weekly.")
	in := Input{Dir: dir, Today: "2026-10-01"}
	want := "baloo:no-stale-adr-date: an ADR's Date is when it last changed:\n" +
		".about/adr/billing.md: changed, but its Date is 2020-01-01; set it to 2026-10-01\n"
	if code, errs := run(t, "no-stale-adr-date", nil, in); code != 1 || errs != want {
		t.Errorf("no-stale-adr-date = %d, %q; want 1, %q", code, errs, want)
	}
	write("2026-10-01", "Invoices are weekly.")
	if code, errs := run(t, "no-stale-adr-date", nil, in); code != 0 || errs != "" {
		t.Errorf("no-stale-adr-date dated today = %d, %q; want 0", code, errs)
	}
}

// The pre-commit Check no-conflict-markers fails with where each marker is.
func TestRun_NoConflictMarkers(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a.go": "<<<<<<< HEAD\n"})
	want := "baloo:no-conflict-markers: resolve each conflict, or give a file that holds markers on " +
		"purpose a longer conflict-marker-size in .gitattributes; conflict markers:\na.go:1\n"
	if code, errs := run(t, "no-conflict-markers", nil, Input{Dir: dir}); code != 1 || errs != want {
		t.Errorf("no-conflict-markers = %d, %q; want 1, %q", code, errs, want)
	}
}

// The pre-commit Check no-large-files fails with each file over the limit the Input gives.
func TestRun_NoLargeFiles(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"app": strings.Repeat("x", 2048)})
	want := "baloo:no-large-files: keep each out of git, or raise no-large-files' max-size in " +
		".claude/baloo.yml:\napp: 2 KB, over 1 KB\n"
	if code, errs := run(t, "no-large-files", nil, Input{Dir: dir, MaxFileKB: 1}); code != 1 || errs != want {
		t.Errorf("no-large-files = %d, %q; want 1, %q", code, errs, want)
	}
	if code, errs := run(t, "no-large-files", nil, Input{Dir: dir}); code != 0 || errs != "" {
		t.Errorf("no-large-files with the default limit = %d, %q; want 0", code, errs)
	}
}

// The pre-push Check linear-history fails with the merge commits the push sends, as git gives them
// on stdin.
func TestRun_LinearHistory(t *testing.T) {
	dir := testkit.Repo(t)
	testkit.Git(t, dir, "commit", "-q", "--allow-empty", "-m", "feat: base")
	testkit.Git(t, dir, "checkout", "-q", "-b", "side")
	testkit.Git(t, dir, "commit", "-q", "--allow-empty", "-m", "feat: side")
	testkit.Git(t, dir, "checkout", "-q", "main")
	base := strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	testkit.Git(t, dir, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
	merge := strings.TrimSpace(testkit.Git(t, dir, "rev-parse", "HEAD"))
	for _, tc := range []struct {
		local, remote string
		code          int
		errs          string
	}{
		{base, strings.Repeat("0", 40), 0, ""},
		{merge, base, 1, "baloo:linear-history: rebase instead of merging, then push the rebased " +
			"branch with --force-with-lease; git config pull.rebase true makes git pull rebase; merge " +
			"commits:\nrefs/heads/main " + merge[:12] + "\n"},
		{strings.Repeat("2", 40), base, 2, "baloo:linear-history: git rev-list: "},
	} {
		pushed := "refs/heads/main " + tc.local + " refs/heads/main " + tc.remote + "\n"
		code, errs := run(t, "linear-history", nil, Input{Dir: dir, Stdin: strings.NewReader(pushed)})
		wrong := errs != tc.errs
		if tc.code == 2 { // after why git failed
			wrong = !strings.HasPrefix(errs, tc.errs)
		}
		if code != tc.code || wrong {
			t.Errorf("linear-history of %q = %d, %q; want %d, %q", pushed, code, errs, tc.code, tc.errs)
		}
	}
}

// A Check the Config turns off passes everything; an unknown Check, or one given arguments it
// doesn't take, is not ok.
func TestRun_OffAndUnknown(t *testing.T) {
	path := message(t, "Add x\n")
	var stderr bytes.Buffer
	off := func(string) bool { return false }
	if code, ok := Run("conventional-commits", []string{path}, Input{}, off, &stderr); code != 0 || !ok ||
		stderr.Len() != 0 {
		t.Errorf("conventional-commits off = %d, %v, %q; want 0, ok and nothing", code, ok, stderr.String())
	}
	for name, args := range map[string][]string{
		"nope":                  nil,
		"conventional-commits":  nil,
		"no-ai-coauthor":        {path, path},
		"no-secrets-in-commits": {path},
	} {
		if _, ok := Run(name, args, Input{}, all, &stderr); ok {
			t.Errorf("Run(%s, %q) ok; want not", name, args)
		}
	}
}

// A Git hook runs each of its Checks, all of them, and fails with the worst; it takes from git's
// arguments only the message file of commit-msg.
func TestRunHook(t *testing.T) {
	path := message(t, "Add x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")
	var stderr bytes.Buffer
	if code, ok := RunHook("commit-msg", []string{path, "extra"}, Input{}, all, &stderr); code != 1 || !ok ||
		!strings.Contains(stderr.String(), "baloo:no-ai-coauthor: ") ||
		!strings.Contains(stderr.String(), "baloo:conventional-commits: ") {
		t.Errorf("commit-msg = %d, %v, %q; want 1, ok and both Checks' findings", code, ok, stderr.String())
	}
	if _, ok := RunHook("commit-msg", nil, Input{}, all, &stderr); ok {
		t.Error("commit-msg without a message file ok; want not")
	}
	if _, ok := RunHook("post-merge", nil, Input{}, all, &stderr); ok {
		t.Error("post-merge ok; want not, the plugin writes no such Git hook")
	}
	dir := testkit.Repo(t)
	stderr.Reset()
	if code, ok := RunHook("pre-push", []string{"origin", "url"}, Input{Dir: dir, Stdin: strings.NewReader("")},
		all, &stderr); code != 0 || !ok || stderr.Len() != 0 {
		t.Errorf("pre-push with nothing pushed = %d, %v, %q; want 0, ok and nothing", code, ok, stderr.String())
	}
}

// Usage names each Check with what it takes.
func TestUsage(t *testing.T) {
	got := strings.Join(Usage(), "\n")
	for _, want := range []string{"check no-ai-coauthor <message file>", "check no-secrets-in-commits\n",
		"check linear-history < <pushed refs>"} {
		if !strings.Contains(got+"\n", want) {
			t.Errorf("Usage() = %q; want it to have %q", got, want)
		}
	}
}

// Each Check a Git hook runs has a name of its own and a Git hook git calls.
func TestGitHookChecks(t *testing.T) {
	gits := []string{"applypatch-msg", "pre-applypatch", "post-applypatch", "pre-commit",
		"pre-merge-commit", "prepare-commit-msg", "commit-msg", "post-commit", "pre-rebase",
		"post-checkout", "post-merge", "pre-push", "pre-auto-gc", "post-rewrite"}
	seen := map[string]bool{}
	for _, c := range gitHookChecks {
		if seen[c.name] {
			t.Errorf("%s is in the registry twice", c.name)
		}
		seen[c.name] = true
		if !slices.Contains(gits, c.hook) {
			t.Errorf("%s runs in %q, which git never calls", c.name, c.hook)
		}
	}
}
