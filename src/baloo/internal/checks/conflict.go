package checks

import (
	"bytes"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

// leftover ends a line of `git diff --check` for a conflict marker.
const leftover = ": leftover conflict marker"

// NoConflictMarkers is the Check baloo:no-conflict-markers (pre-commit): `<path>:<line>` for each
// conflict marker the staged changes of the repo `dir` add, as git's own `diff --check` finds
// them, in a file where one of them opens or closes a conflict: a Markdown heading underlined
// with `=======` alone passes, and so does a file whose conflict-marker-size in .gitattributes is
// longer. It errs where git does, such as outside a repo.
func NoConflictMarkers(dir string) ([]string, error) {
	var stdout, stderr bytes.Buffer
	cmd := exec.Command("git", "-C", dir, "-c", "core.quotePath=false",
		"diff", "--cached", "--check", "--no-color")
	cmd.Env = append(os.Environ(), "LC_ALL=C") // git's own words, which the lines are told by
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	// It exits 2 where it finds a marker or a whitespace error.
	var exit *exec.ExitError
	if err := cmd.Run(); err != nil && !(errors.As(err, &exit) && exit.ExitCode() == 2) {
		return nil, fmt.Errorf("git diff: %v: %s", err, strings.TrimSpace(stderr.String()))
	}
	var paths []string
	lines := map[string][]int{}
	for _, text := range strings.Split(stdout.String(), "\n") {
		at, ok := strings.CutSuffix(text, leftover)
		i := strings.LastIndexByte(at, ':')
		if !ok || i < 0 {
			continue
		}
		path := at[:i]
		n, err := strconv.Atoi(at[i+1:])
		if err != nil {
			continue
		}
		if lines[path] == nil {
			paths = append(paths, path)
		}
		lines[path] = append(lines[path], n)
	}
	var found []string
	for _, path := range paths {
		if !opensConflict(dir, path, lines[path]) {
			continue
		}
		for _, n := range lines[path] {
			found = append(found, fmt.Sprintf("%s:%d", path, n))
		}
	}
	return found, nil
}

// opensConflict says whether one of the lines `lines` of the staged file `path` opens or closes a
// conflict, `<<<<<<<` or `>>>>>>>`; it says so too where the file can't be read, such as a path
// git quoted.
func opensConflict(dir, path string, lines []int) bool {
	text, err := git(dir, "cat-file", "blob", ":"+path)
	if err != nil {
		return true
	}
	all := strings.Split(text, "\n")
	for _, n := range lines {
		if n >= 1 && n <= len(all) && (strings.HasPrefix(all[n-1], "<") || strings.HasPrefix(all[n-1], ">")) {
			return true
		}
	}
	return false
}
