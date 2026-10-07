package review

// cspell:ignore dont ndont

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// fakeClaude is a `claude` that writes what it was run with into the folder `seen`: its arguments,
// one per line, its folder, the Session review's own environment variable and its stdin; then
// replies `reply`.
func fakeClaude(t *testing.T, reply string) (claude, seen string) {
	t.Helper()
	seen = t.TempDir()
	claude = filepath.Join(t.TempDir(), "claude")
	script := "#!/bin/sh\n" +
		"printf '%s\\n' \"$@\" > " + seen + "/args\n" +
		"pwd > " + seen + "/pwd\n" +
		"echo \"$" + Env + "\" > " + seen + "/env\n" +
		"cat > " + seen + "/stdin\n" +
		"printf '" + reply + "'\n"
	if err := os.WriteFile(claude, []byte(script), 0o755); err != nil {
		t.Fatal(err)
	}
	return claude, seen
}

// conversation is a Transcript of a session `chars` characters long in all, with a Secret.
func conversation(chars int) []byte {
	text := "AKIA" + "IOSFODNN7EXAMPLE " + strings.Repeat("x", chars) // cspell:disable-line
	return []byte(`{"type":"user","message":{"content":"` + text + `"}}` + "\n")
}

// wait waits until no Session review of the repo at `root` runs.
func wait(t *testing.T, root, data string) {
	t.Helper()
	for deadline := time.Now().Add(5 * time.Second); time.Now().Before(deadline); time.Sleep(20 * time.Millisecond) {
		if !Running(root, data) {
			return
		}
	}
	t.Fatal("the Session review still runs after 5s")
}

// A review runs headless at the repo's root, may write only its Proposals, and keeps its reply in
// a file of its own id, which the next review leaves alone.
func TestStart_RunsAHeadlessReviewThatWritesOnlyProposals(t *testing.T) {
	claude, seen := fakeClaude(t, "P1 adds Order to the glossary.\n")
	root, _ := filepath.EvalSymlinks(testkit.Repo(t))
	data := t.TempDir()
	for _, session := range []string{"aaaaaaaa-1", "bbbbbbbb-2"} {
		started, err := Start(claude, "/plugins/baloo", root, data, session, conversation(3000))
		if !started || err != nil {
			t.Fatalf("Start = %t, %v; want started", started, err)
		}
		wait(t, root, data)
	}
	replies, _ := filepath.Glob(filepath.Join(folder(root, data), "*.txt"))
	if len(replies) != 2 {
		t.Fatalf("replies = %q; want one per review", replies)
	}
	for _, r := range replies {
		if text, _ := os.ReadFile(r); string(text) != "P1 adds Order to the glossary.\n" {
			t.Errorf("%s = %q; want the review's reply", r, text)
		}
	}
	read := func(name string) string {
		text, _ := os.ReadFile(filepath.Join(seen, name))
		return string(text)
	}
	if got := read("pwd"); got != root+"\n" {
		t.Errorf("the review ran in %q, want the root %q", got, root)
	}
	if got := read("env"); got != "1\n" {
		t.Errorf("%s in the review = %q, want 1, so it starts no review of its own", Env, got)
	}
	if got := read("stdin"); !strings.HasPrefix(got, "user: ***** xxx") {
		t.Errorf("the review read %.40q…, want the conversation masked", got)
	}
	args := read("args")
	for _, want := range []string{"-p", "--plugin-dir\n/plugins/baloo\n", "--tools\nRead,Glob,Grep,Edit,Write,Skill\n",
		"--permission-mode\ndontAsk\n", "Edit(./.about/proposals/**)\n", "./.about/proposals/" + filepath.Base(strings.TrimSuffix(replies[1], ".txt")) + ".md"} {
		if !strings.Contains(args, want) {
			t.Errorf("the review's arguments =\n%s\nwant %q among them", args, want)
		}
	}
	for _, not := range []string{"Bash", "glossary.md)", "inbox.md)", "adr/**)"} {
		if strings.Contains(args, not) {
			t.Errorf("the review's arguments =\n%s\nwant no %q: it writes only its Proposals", args, not)
		}
	}
	exclude, _ := os.ReadFile(filepath.Join(root, ".git", "info", "exclude"))
	if !strings.Contains(string(exclude), "\n/.about/proposals\n") && !strings.HasPrefix(string(exclude), "/.about/proposals\n") {
		t.Errorf("info/exclude = %q; want the Proposals left out of git", exclude)
	}
}

// A session too short to have settled much, or a headless one, gets no review.
func TestStart_SkipsAShortOrHeadlessSession(t *testing.T) {
	claude, seen := fakeClaude(t, "")
	headless := []byte(`{"type":"user","entrypoint":"sdk-cli","message":{"content":"` + strings.Repeat("x", 3000) + `"}}` + "\n")
	for _, transcript := range [][]byte{conversation(1000), headless} {
		if started, err := Start(claude, "/plugins/baloo", testkit.Repo(t), t.TempDir(), "s", transcript); started || err != nil {
			t.Errorf("Start = %t, %v; want no review", started, err)
		}
	}
	if _, err := os.Stat(filepath.Join(seen, "args")); err == nil {
		t.Error("claude ran; want it not run")
	}
}

const proposals = `# Session review R1

## P1 · inbox · add · .about/inbox.md · No evals

Why: found and not fixed.

After:
~~~markdown
## No evals

2026-10-07 · session review

Nothing measures the skills.
~~~

## P2 · glossary · edit · .about/glossary.md · Order

Why: agreed.

Before:
~~~markdown
**Order**:
A thing.
~~~

After:
~~~markdown
**Order**:
A request to buy.
~~~

## P3 · adr · delete · .about/adr/gone.md · Gone

Before:
~~~markdown
An old rule.
~~~

## P4 · notes · add · notes.md · Elsewhere

After:
~~~markdown
x
~~~
`

func TestParse(t *testing.T) {
	got := Parse("R1", []byte(proposals))
	if len(got) != 4 {
		t.Fatalf("Parse = %d proposals; want 4", len(got))
	}
	want := Proposal{Review: "R1", ID: "P2", Target: "glossary", Kind: "edit", Path: ".about/glossary.md",
		Title: "Order", Before: "**Order**:\nA thing.\n", After: "**Order**:\nA request to buy.\n"}
	if got[1] != want {
		t.Errorf("Parse's P2 = %+v; want %+v", got[1], want)
	}
	if got[0].Problem != "" || got[2].Problem != "" || got[3].Problem == "" {
		t.Errorf("Parse's problems = %q, %q, %q, %q; want only P4's", got[0].Problem, got[1].Problem,
			got[2].Problem, got[3].Problem)
	}
	for _, bad := range []string{"## P1 inbox add\n", "## P1 · adr · add · .about/adr/../x.md · X\nAfter:\n~~~\nx\n~~~\n",
		"## P1 · inbox · edit · .about/inbox.md · X\nAfter:\n~~~\nx\n~~~\n"} {
		if p := Parse("R", []byte(bad)); len(p) != 1 || p[0].Problem == "" {
			t.Errorf("Parse(%q) = %+v; want one it can't read", bad, p)
		}
	}
}

// repoWith is a repo with an origin carrying a token, the glossary and the ADR the Proposals change,
// and their file.
func repoWith(t *testing.T) string {
	t.Helper()
	root := testkit.Repo(t)
	testkit.Git(t, root, "remote", "add", "origin", "https://user:token@github.com/o/r.git") // baloo:allow-secret: a fake token, for Repo to drop
	for path, text := range map[string]string{
		names.Glossary:               "# Glossary\n\n**Order**:\nA thing.\n",
		names.ADRs + "gone.md":       "# Gone\n\nAn old\nrule.\n",
		names.Inbox:                  "",
		names.Proposals + "R1.md":    proposals,
		names.Proposals + "R0.md":    "# Session review R0\n",
		names.Proposals + "keep.txt": "",
	} {
		file := filepath.Join(root, path)
		if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(file, []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

// show is what Show tells the session `session`, as one text.
func show(root, data, session string) string {
	return strings.Join(Show(root, data, session, "decide"), "\n")
}

// The Proposals are shown once a session, until each is decided; the log gets a line a decision,
// with the repo's origin; the file goes once each is decided and applied.
func TestShowAndDecide(t *testing.T) {
	root, data := repoWith(t), t.TempDir()
	t.Setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
	got := show(root, data, "s1")
	for _, want := range []string{"`decide <review> <id> accepted|accepted-edited|rejected|deferred`",
		"  R1 P1 inbox add .about/inbox.md: No evals\n", "  R1 P2 glossary edit .about/glossary.md: Order\n",
		"  R1 P3 adr delete .about/adr/gone.md: Gone\n", "  R1 P4: can't be read, its target is"} {
		if !strings.Contains(got+"\n", want) {
			t.Errorf("Show =\n%s\nwant it to hold %q", got, want)
		}
	}
	if again := show(root, data, "s1"); again != "" {
		t.Errorf("Show again in the same session = %q; want nothing new", again)
	}
	if other := show(root, data, "s2"); other != got {
		t.Errorf("Show in another session = %q; want the same list", other)
	}
	t.Setenv("CLAUDE_CODE_ENTRYPOINT", "sdk-cli")
	if headless := show(root, data, "s3"); headless != "" {
		t.Errorf("Show in a headless session = %q; want nothing", headless)
	}
	t.Setenv("CLAUDE_CODE_ENTRYPOINT", "cli")

	// P2 applied in other words, which its Applied records, P3 deferred twice, then neither
	// deferred again nor accepted unread.
	glossary := filepath.Join(root, names.Glossary)
	os.WriteFile(glossary, []byte("# Glossary\n\n**Order**:\nA customer's\nrequest to buy.\n"), 0o644)
	steps := []struct{ id, decision, err string }{
		{"P2", AcceptedEdited, "has no Applied block"},
	}
	file := filepath.Join(root, names.Proposals, "R1.md")
	text, _ := os.ReadFile(file)
	withApplied := strings.Replace(string(text), "## P3 ", "Applied:\n~~~markdown\n**Order**:\nA customer's request to buy.\n~~~\n\n## P3 ", 1)
	steps = append(steps, []struct{ id, decision, err string }{
		{"P2", AcceptedEdited, ""},
		{"P3", Deferred, ""},
		{"P3", Deferred, ""},
		{"P3", Deferred, "deferred 2 times already"},
		{"P4", Accepted, "can't be read"},
		{"P9", Rejected, "no proposal P9"},
		{"P1", "maybe", "is not accepted, accepted-edited, rejected or deferred"},
	}...)
	for i, s := range steps {
		if i == 1 {
			os.WriteFile(file, []byte(withApplied), 0o644)
		}
		_, err := Decide(root, data, "R1", s.id, s.decision)
		if (err == nil) != (s.err == "") || err != nil && !strings.Contains(err.Error(), s.err) {
			t.Errorf("Decide(%s, %s) = %v; want %q", s.id, s.decision, err, s.err)
		}
	}
	if got := show(root, data, "s4"); !strings.Contains(got, "R1 P3 adr delete .about/adr/gone.md: Gone (deferred 2×)") ||
		strings.Contains(got, "R1 P2") {
		t.Errorf("Show after the decisions =\n%s\nwant P3 deferred twice, and no P2", got)
	}
	log, _ := os.ReadFile(logFile(data))
	lines := strings.Split(strings.TrimSpace(string(log)), "\n")
	if len(lines) != 3 {
		t.Fatalf("log = %q; want a line per decision logged", log)
	}
	if f := strings.Split(lines[0], "\t"); len(f) != 7 || f[1] != "https://github.com/o/r.git" ||
		!slices.Equal(f[2:], []string{"R1", "P2", "glossary", "edit", "accepted-edited"}) {
		t.Errorf("log line = %q; want when, the origin without its token, R1, P2, glossary, edit, accepted-edited", f)
	}

	// Accepting an add the file doesn't hold yet is a mismatch until it is applied.
	todo, err := Decide(root, data, "R1", "P1", Accepted)
	if err != nil || !strings.Contains(todo, "accepted, but its After is not in .about/inbox.md") {
		t.Errorf("Decide(P1) = %q, %v; want the mismatch to fix", todo, err)
	}
	if got := show(root, data, "s4"); !strings.Contains(got, "mismatch: R1 P1, accepted, but its After is not in") {
		t.Errorf("Show = %q; want the mismatch", got)
	}
	os.WriteFile(filepath.Join(root, names.Inbox), []byte("## No evals\n\n2026-10-07 · session review\n\nNothing measures the skills.\n"), 0o644)
	os.WriteFile(filepath.Join(root, names.ADRs, "gone.md"), []byte("# Gone\n"), 0o644)
	for _, id := range []string{"P3", "P4"} {
		if _, err := Decide(root, data, "R1", id, map[string]string{"P3": Accepted, "P4": Rejected}[id]); err != nil {
			t.Errorf("Decide(%s) = %v", id, err)
		}
	}
	if _, err := os.Stat(file); err == nil {
		t.Error("R1.md is still there; want it gone once each Proposal is decided and applied")
	}
	if kept, err := os.ReadFile(filepath.Join(folder(root, data), "decided", "R1.md")); err != nil ||
		string(kept) != withApplied {
		t.Errorf("decided/R1.md = %q, %v; want the file kept as it was decided", kept, err)
	}
	if _, err := os.Stat(filepath.Join(root, names.Proposals, "keep.txt")); err != nil {
		t.Error("the folder went with a file still in it")
	}
}

// An edit whose Before is gone is stale and can't be accepted; one applied with no decision logged
// is a mismatch.
func TestStaleAndUndecidedProposals(t *testing.T) {
	root, data := repoWith(t), t.TempDir()
	os.WriteFile(filepath.Join(root, names.Glossary), []byte("# Glossary\n\n**Order**:\nSomething else.\n"), 0o644)
	got := show(root, data, "s1")
	if !strings.Contains(got, "R1 P2 glossary edit .about/glossary.md: Order (stale: ") {
		t.Errorf("Show =\n%s\nwant P2 stale", got)
	}
	if _, err := Decide(root, data, "R1", "P2", Accepted); err == nil || !strings.Contains(err.Error(), "stale") {
		t.Errorf("Decide(stale P2, accepted) = %v; want it refused", err)
	}
	if _, err := Decide(root, data, "R1", "P2", Rejected); err != nil {
		t.Errorf("Decide(stale P2, rejected) = %v", err)
	}
	os.WriteFile(filepath.Join(root, names.Inbox), []byte("## No evals\n\n2026-10-07 · session review\n\nNothing measures the skills.\n"), 0o644)
	if got := show(root, data, "s2"); !strings.Contains(got, "mismatch: R1 P1, its After is in .about/inbox.md, but no decision is logged") {
		t.Errorf("Show =\n%s\nwant the undecided P1 as a mismatch", got)
	}
}

// A log written before it had fields is moved aside, so each line of the log parses.
func TestDecide_MovesAnOldLogAside(t *testing.T) {
	root, data := repoWith(t), t.TempDir()
	os.MkdirAll(filepath.Dir(logFile(data)), 0o700)
	os.WriteFile(logFile(data), []byte("--- 2026-10-05T19:12:20Z /x\n"), 0o600)
	if _, err := Decide(root, data, "R1", "P2", Rejected); err != nil {
		t.Fatal(err)
	}
	old, _ := os.ReadFile(logFile(data) + ".old")
	log, _ := os.ReadFile(logFile(data))
	if string(old) != "--- 2026-10-05T19:12:20Z /x\n" || strings.Count(string(log), "\t") != 6 {
		t.Errorf("log = %q, old = %q; want the old one aside and one line of fields", log, old)
	}
}

// Without an origin, the log names the repo by its root.
func TestRepo(t *testing.T) {
	root := testkit.Repo(t)
	if got := Repo(root); got != root {
		t.Errorf("Repo without an origin = %q; want %q", got, root)
	}
	testkit.Git(t, root, "remote", "add", "origin", "git@github.com:o/r.git")
	if got := Repo(root); got != "git@github.com:o/r.git" {
		t.Errorf("Repo = %q; want the origin", got)
	}
}
