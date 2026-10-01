// Package binlink is the link in the plugin's data folder to the binary, which session start points
// at the binary running it: what the Status line and the Git hooks run, so their command stays the
// same from one version to the next (ADR status-line, ADR git-hooks).
package binlink

import (
	"errors"
	"os"
	"path/filepath"
	"strconv"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Point points the link in `data`, the plugin's data folder, at the binary running it, and returns
// the link's path. The new link replaces the old in one step, so a command run meanwhile finds one
// or the other.
func Point(data string) (string, error) {
	if data == "" {
		return "", errors.New("CLAUDE_PLUGIN_DATA is not set")
	}
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	path := filepath.Join(data, names.Plugin)
	if got, err := os.Readlink(path); err == nil && got == exe {
		return path, nil
	}
	tmp := path + "." + strconv.Itoa(os.Getpid()) + ".tmp"
	os.Remove(tmp)
	if err := os.Symlink(exe, tmp); err != nil {
		return "", err
	}
	if err := os.Rename(tmp, path); err != nil {
		os.Remove(tmp)
		return "", err
	}
	return path, nil
}
