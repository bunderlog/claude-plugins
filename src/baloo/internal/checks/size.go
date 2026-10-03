package checks

// cspell:ignore objectsize

import (
	"bytes"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// DefaultMaxFileKB is the largest file no-large-files lets a commit add without a setting, in KB.
const DefaultMaxFileKB = 1024

// NoLargeFiles is the Check baloo:no-large-files (pre-commit): `<path>: <size> KB, over <max>
// KB` for each file the staged changes of the repo `dir` add over `maxKB` KB, of 1024 bytes;
// DefaultMaxFileKB for 0. A file already committed passes, changed or renamed too, and so does a
// submodule. It errs where git does, such as outside a repo.
func NoLargeFiles(dir string, maxKB int) ([]string, error) {
	if maxKB == 0 {
		maxKB = DefaultMaxFileKB
	}
	// Each file added is `:<old mode> <new mode> <old id> <new id> A`, then its path.
	raw, err := git(dir, "diff", "--cached", "-M", "--diff-filter=A", "--raw", "-z", "--no-abbrev")
	if err != nil {
		return nil, err
	}
	var paths []string
	var ids strings.Builder
	fields := strings.Split(strings.TrimSuffix(raw, "\x00"), "\x00")
	for i := 0; i+1 < len(fields); i += 2 {
		f := strings.Fields(fields[i])
		if len(f) != 5 || f[1] == "160000" {
			continue
		}
		paths = append(paths, fields[i+1])
		ids.WriteString(f[3])
		ids.WriteByte('\n')
	}
	if paths == nil {
		return nil, nil
	}
	var stdout, stderr bytes.Buffer
	cmd := exec.Command("git", "-C", dir, "cat-file", "--batch-check=%(objectsize)")
	cmd.Stdin, cmd.Stdout, cmd.Stderr = strings.NewReader(ids.String()), &stdout, &stderr
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("git cat-file: %v: %s", err, strings.TrimSpace(stderr.String()))
	}
	var found []string
	for i, line := range strings.Split(strings.TrimSuffix(stdout.String(), "\n"), "\n") {
		size, err := strconv.Atoi(line)
		if err != nil || i >= len(paths) {
			return nil, fmt.Errorf("git cat-file: %q is not a size", line)
		}
		if size > maxKB*1024 {
			found = append(found, fmt.Sprintf("%s: %d KB, over %d KB", paths[i], (size+1023)/1024, maxKB))
		}
	}
	return found, nil
}
