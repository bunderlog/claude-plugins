// Package stopcheck is the Stop check (ADR stop-check): at each prompt it marks the state of the
// working tree, and when Claude ends the turn, runs the project's command if the tree changed.
package stopcheck

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
)

// tail is how much of the command's output, from its end, a failure hands back.
const tail = 4000

// session is a session id fit to name a file.
var session = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)

// Mark records the state of the working tree of the repo at `root` for the session `id`, in `data`,
// the plugin's data folder, for its next Check.
func Mark(root, data, id string) error {
	path, err := markPath(data, id)
	if err != nil {
		return err
	}
	snap, err := snapshot(root)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, []byte(snap), 0o644)
}

// Check runs `command` with sh in the repo at `root` when its working tree is no longer as the
// session `id`'s last Mark recorded, and returns what to hand back to Claude when it fails: the
// command, its exit status and the end of its output, ending in a newline. The Mark serves one Check: without one, it
// runs nothing.
func Check(root, data, id, command string) (failure string, err error) {
	path, err := markPath(data, id)
	if err != nil {
		return "", err
	}
	marked, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	if err := os.Remove(path); err != nil {
		return "", err
	}
	snap, err := snapshot(root)
	if err != nil || snap == string(marked) {
		return "", err
	}
	cmd := exec.Command("sh", "-c", command)
	cmd.Dir = root
	out, err := cmd.CombinedOutput()
	if err == nil {
		return "", nil
	}
	if len(out) > tail {
		out = out[len(out)-tail:]
		if i := bytes.IndexByte(out, '\n'); i >= 0 {
			out = out[i+1:]
		}
	}
	if len(out) > 0 && !bytes.HasSuffix(out, []byte("\n")) {
		out = append(out, '\n')
	}
	return fmt.Sprintf("`%s` failed with %v:\n%s", command, err, out), nil
}

func markPath(data, id string) (string, error) {
	if !session.MatchString(id) {
		return "", fmt.Errorf("session id %q is not a plain name", id)
	}
	if data == "" {
		return "", errors.New("CLAUDE_PLUGIN_DATA is not set")
	}
	return filepath.Join(data, "stop-check", id), nil
}

// snapshot is a digest of the working tree of the repo at `root`: its HEAD, its `git status`, and
// the content of each file the status lists; ignored files are not in it.
func snapshot(root string) (string, error) {
	head, _ := exec.Command("git", "-C", root, "rev-parse", "-q", "--verify", "HEAD").Output()
	status, err := exec.Command("git", "-C", root, "status", "--porcelain=v1", "-z",
		"--untracked-files=all").Output()
	if err != nil {
		return "", fmt.Errorf("git status: %w", err)
	}
	h := sha256.New()
	h.Write(head)
	h.Write(status)
	entries := bytes.Split(bytes.TrimSuffix(status, []byte{0}), []byte{0})
	for i := 0; i < len(entries); i++ {
		e := entries[i]
		if len(e) < 4 {
			continue
		}
		if e[0] == 'R' || e[0] == 'C' {
			i++ // the path it was renamed or copied from
		}
		h.Write(e)
		if content, err := os.ReadFile(filepath.Join(root, string(e[3:]))); err == nil {
			sum := sha256.Sum256(content)
			h.Write(sum[:])
		}
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
