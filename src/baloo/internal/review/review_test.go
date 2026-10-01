package review

// cspell:ignore dont ndont

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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

// wait waits until the last Session review at `root` is done, and returns what Last says then.
func wait(t *testing.T, root, data string) []string {
	t.Helper()
	for deadline := time.Now().Add(5 * time.Second); time.Now().Before(deadline); time.Sleep(20 * time.Millisecond) {
		if last := Last(root, data); len(last) == 0 || !strings.Contains(last[0], "still running") {
			return last
		}
	}
	t.Fatal("the Session review still runs after 5s")
	return nil
}

func TestStart_RunsAHeadlessReviewAtTheRootAndLastSaysWhatItChanged(t *testing.T) {
	claude, seen := fakeClaude(t, "Added Order to the glossary.\n")
	root, _ := filepath.EvalSymlinks(t.TempDir())
	data := t.TempDir()
	started, err := Start(claude, "/plugins/baloo", root, data, conversation(3000))
	if !started || err != nil {
		t.Fatalf("Start = %t, %v; want started", started, err)
	}
	last := wait(t, root, data)
	if len(last) != 2 || !strings.HasPrefix(last[0], "the Session review of the last session (") ||
		last[1] != "  Added Order to the glossary." {
		t.Errorf("Last = %q, want its header and the reply", last)
	}
	if again := Last(root, data); again != nil {
		t.Errorf("Last a second time = %q, want nothing: it says so once", again)
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
	for _, want := range []string{"-p", "--plugin-dir\n/plugins/baloo\n", "--tools\nRead,Glob,Grep,Edit,Write,Bash,Skill\n", "--permission-mode\ndontAsk\n",
		"Edit(./.about/glossary.md)\n", "Edit(./.about/adr/**)\n", "Edit(./.about/inbox.md)\n",
		"Bash(rm ./.about/inbox.md)\n"} {
		if !strings.Contains(args, want) {
			t.Errorf("the review's arguments =\n%s\nwant %q among them", args, want)
		}
	}
}

// A session too short to have settled much, or a headless one, gets no review.
func TestStart_SkipsAShortOrHeadlessSession(t *testing.T) {
	claude, seen := fakeClaude(t, "")
	headless := []byte(`{"type":"user","entrypoint":"sdk-cli","message":{"content":"` + strings.Repeat("x", 3000) + `"}}` + "\n")
	for _, transcript := range [][]byte{conversation(1000), headless} {
		if started, err := Start(claude, "/plugins/baloo", t.TempDir(), t.TempDir(), transcript); started || err != nil {
			t.Errorf("Start = %t, %v; want no review", started, err)
		}
	}
	if _, err := os.Stat(filepath.Join(seen, "args")); err == nil {
		t.Error("claude ran; want it not run")
	}
}

func TestLast_SaysNothingWithoutAReview(t *testing.T) {
	if last := Last(t.TempDir(), t.TempDir()); last != nil {
		t.Errorf("Last = %q, want nothing", last)
	}
}
