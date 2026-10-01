// Package statusline is the plugin's Status line (ADR status-line): the line the binary draws from
// what Claude Code gives a status line command, and the command set in a project's settings.
package statusline

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// line is Claude Code's statusLine setting.
type line struct {
	Type    string `json:"type"`
	Command string `json:"command"`
	Padding int    `json:"padding"`
}

// command is the status line command that runs the binary at `bin`, marked as the plugin's.
func command(bin string) string {
	return "'" + strings.ReplaceAll(bin, "'", `'\''`) + "' status-line " + names.Marker
}

// ours says whether the statusLine setting `raw` is one the plugin wrote.
func ours(raw json.RawMessage) bool {
	var l line
	return json.Unmarshal(raw, &l) == nil && strings.HasSuffix(l.Command, " "+names.Marker)
}

// Set sets the status line of the project at `project`, in the repo at `root`, or takes it out, as
// `on`, the Config's key, says. On, it sets the plugin's in the project's settings.local.json,
// where the plugin is enabled in its local, project or user settings and none of its local, project
// or managed settings has a status line the plugin didn't write; the user's own gives way. Off, or
// where one of those has a status line of its own, it takes the plugin's out. It says whether it
// set one where the plugin's wasn't.
//
// The command runs the binary through a link in `data`, the plugin's data folder, which Set
// points at the binary running it, so the command stays the same from one version to the next.
func Set(project, root, data string, on bool) (shown bool, err error) {
	files := settings.Files(project)
	fields, err := settings.ReadAll(files)
	if err != nil {
		return false, err
	}
	local := files[settings.Local]
	current, had := fields[settings.Local]["statusLine"]
	mine := had && ours(current)
	theirs := had && !mine
	for _, scope := range []settings.Scope{settings.Project, settings.Managed} {
		if _, ok := fields[scope]["statusLine"]; ok {
			theirs = true
		}
	}
	if !on || theirs {
		if mine {
			return false, settings.Delete(local, "statusLine")
		}
		return false, nil
	}
	if !mine && settings.Enabling(fields) == "" {
		return false, nil
	}
	if data == "" {
		return false, errors.New("CLAUDE_PLUGIN_DATA is not set")
	}
	bin, err := relink(data)
	if err != nil {
		return false, err
	}
	want := line{"command", command(bin), 0}
	var got line
	if mine && json.Unmarshal(current, &got) == nil && got == want {
		return false, nil
	}
	created, err := settings.Set(local, "statusLine", want)
	if err != nil {
		return false, err
	}
	if created {
		err = settings.Exclude(root, local)
	}
	return !mine, err
}

// relink points the link in `data` at the binary running it, and returns the link's path. The
// new link replaces the old in one step, so a status line drawn meanwhile finds one or the other.
func relink(data string) (string, error) {
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
