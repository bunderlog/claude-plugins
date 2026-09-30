// Package testkit makes temporary git repos for tests, cut off from the machine's git: no config
// of the machine's applies, commits are unsigned, and no GIT_ variable the tests ran with, such as
// the GIT_DIR or GIT_INDEX_FILE of a Git hook that runs them, reaches git.
package testkit

import (
	"os"
	"os/exec"
	"strings"
	"testing"
)

// Repo is a new repo in a temporary folder, on the branch main, for the test `t`; until the test
// ends, git run by it or by the code it tests sees only the environment Repo sets.
func Repo(t *testing.T) string {
	t.Helper()
	for _, kv := range os.Environ() {
		if k, v, _ := strings.Cut(kv, "="); strings.HasPrefix(k, "GIT_") {
			t.Setenv(k, v) // put back when the test ends
			os.Unsetenv(k)
		}
	}
	for k, v := range map[string]string{
		"GIT_CONFIG_GLOBAL":   os.DevNull,
		"GIT_CONFIG_NOSYSTEM": "1",
		"GIT_AUTHOR_NAME":     "t",
		"GIT_AUTHOR_EMAIL":    "t@example.com",
		"GIT_COMMITTER_NAME":  "t",
		"GIT_COMMITTER_EMAIL": "t@example.com",
	} {
		t.Setenv(k, v)
	}
	dir := t.TempDir()
	Git(t, dir, "init", "-q", "-b", "main")
	return dir
}

// Git runs git in `dir` with `args`, and returns what it prints, failing the test when it fails.
func Git(t *testing.T, dir string, args ...string) string {
	t.Helper()
	out, err := exec.Command("git", append([]string{"-C", dir}, args...)...).CombinedOutput()
	if err != nil {
		t.Fatalf("git %s: %v\n%s", strings.Join(args, " "), err, out)
	}
	return string(out)
}
