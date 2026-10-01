package stopcheck

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

// ran is a command that records in a file outside the repo that it ran, then exits with `code`,
// and the file.
func ran(t *testing.T, code string) (command, record string) {
	t.Helper()
	record = filepath.Join(t.TempDir(), "ran")
	return "echo ran >> '" + record + "'; echo 'it failed here'; exit " + code, record
}

func didRun(t *testing.T, record string) bool {
	t.Helper()
	_, err := os.Stat(record)
	return err == nil
}

// A turn that changes the working tree, any way, runs the command, and a failure is handed back
// with what the command printed; one that changes nothing runs nothing.
func TestCheck_RunsTheCommandAfterAChange(t *testing.T) {
	for name, change := range map[string]func(t *testing.T, root string){
		"nothing": func(*testing.T, string) {},
		"an edit": func(t *testing.T, root string) { write(t, filepath.Join(root, "a"), "a2\n") },
		"a second edit of a changed file": func(t *testing.T, root string) {
			write(t, filepath.Join(root, "b"), "b3\n")
		},
		"a new file": func(t *testing.T, root string) { write(t, filepath.Join(root, "c"), "c\n") },
		"a commit":   func(t *testing.T, root string) { testkit.Git(t, root, "commit", "-qam", "x") },
		"a deletion": func(t *testing.T, root string) { os.Remove(filepath.Join(root, "a")) },
		"an ignored file": func(t *testing.T, root string) {
			write(t, filepath.Join(root, "build.log"), "x\n")
		},
	} {
		t.Run(name, func(t *testing.T) {
			root, data := testkit.Repo(t), t.TempDir()
			write(t, filepath.Join(root, ".gitignore"), "*.log\n")
			write(t, filepath.Join(root, "a"), "a\n")
			write(t, filepath.Join(root, "b"), "b\n")
			testkit.Git(t, root, "add", ".")
			testkit.Git(t, root, "commit", "-qm", "init")
			write(t, filepath.Join(root, "b"), "b2\n") // the user's, before the turn
			if err := Mark(root, data, "s1"); err != nil {
				t.Fatal(err)
			}
			change(t, root)
			command, record := ran(t, "3")
			failure, err := Check(root, data, "s1", command)
			changed := name != "nothing" && name != "an ignored file"
			if err != nil || didRun(t, record) != changed {
				t.Fatalf("Check after %s = %q, %v, ran %v; want it run: %v", name, failure, err, didRun(t, record), changed)
			}
			if changed && (!strings.Contains(failure, "exit status 3") || !strings.Contains(failure, "it failed here")) {
				t.Errorf("Check after %s = %q; want the exit status and what the command printed", name, failure)
			}
			if !changed && failure != "" {
				t.Errorf("Check after %s = %q; want no failure", name, failure)
			}
		})
	}
}

// A command that passes hands nothing back, and a Stop without a mark from the turn's prompt runs
// nothing: each mark serves one Stop.
func TestCheck_PassesAndOnlyOnce(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	if err := Mark(root, data, "s1"); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(root, "a"), "a\n")
	command, record := ran(t, "0")
	if failure, err := Check(root, data, "s1", command); failure != "" || err != nil || !didRun(t, record) {
		t.Errorf("Check with a passing command = %q, %v, ran %v; want it run and nothing back", failure, err, didRun(t, record))
	}
	command, record = ran(t, "1")
	write(t, filepath.Join(root, "a"), "a2\n")
	if failure, err := Check(root, data, "s1", command); failure != "" || err != nil || didRun(t, record) {
		t.Errorf("second Check of the turn = %q, %v, ran %v; want nothing run", failure, err, didRun(t, record))
	}
	if failure, err := Check(root, data, "other", command); failure != "" || err != nil || didRun(t, record) {
		t.Errorf("Check of a session never marked = %q, %v, ran %v; want nothing run", failure, err, didRun(t, record))
	}
}

// Only the end of a long output is handed back.
func TestCheck_KeepsTheEndOfTheOutput(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	if err := Mark(root, data, "s1"); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(root, "a"), "a\n")
	failure, err := Check(root, data, "s1", "seq 1 5000; echo the last line; exit 1")
	if err != nil || len(failure) > 5000 || !strings.HasSuffix(failure, "the last line\n") || strings.Contains(failure, "\n1\n") {
		t.Errorf("Check = %d bytes ending %q, %v; want at most 5000, ending with the last line", len(failure), failure[max(0, len(failure)-40):], err)
	}
}

// A session id that isn't a plain name marks nothing outside the data folder.
func TestMark_RefusesAPath(t *testing.T) {
	root, data := testkit.Repo(t), t.TempDir()
	if err := Mark(root, data, "../x"); err == nil {
		t.Error("Mark with ../x = nil; want an error")
	}
}
