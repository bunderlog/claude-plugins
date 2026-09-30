package statusline

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// sandbox is a temporary repo with the user's and the managed settings of its own, none of them
// there yet, and a plugin data folder; it returns the repo's root, Claude Code's own folder and
// the data folder.
func sandbox(t *testing.T) (root, own, data string) {
	t.Helper()
	root, own, data = t.TempDir(), t.TempDir(), t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CLAUDE_CONFIG_DIR", own)
	t.Setenv("BALOO_MANAGED_SETTINGS", filepath.Join(own, "managed-settings.json"))
	return root, own, data
}

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func contents(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	return string(data)
}

// statusLine is the command of the statusLine in the settings file at `path`, or "" for none.
func statusLine(t *testing.T, path string) string {
	t.Helper()
	var fields struct{ StatusLine *line }
	if text := contents(t, path); text != "" {
		if err := json.Unmarshal([]byte(text), &fields); err != nil {
			t.Fatalf("%s is not JSON: %v\n%s", path, err, text)
		}
	}
	if fields.StatusLine == nil {
		return ""
	}
	return fields.StatusLine.Command
}

const on = `{"enabledPlugins": {"` + names.PluginID + `": true}}`
const theirs = `{"statusLine": {"type": "command", "command": "their-line"}}`

func TestSync(t *testing.T) {
	for _, tc := range []struct {
		name                         string
		local, project, user, manage string
		shown                        bool
	}{
		{"enabled in the project", "", on, "", "", true},
		{"enabled here", on, "", "", "", true},
		{"enabled for the user, who has a status line", "", "", `{"statusLine": {"type": "command", "command": "x"}, "enabledPlugins": {"` + names.PluginID + `": true}}`, "", true},
		{"not enabled anywhere", "", "", "", "", false},
		{"enabled only by managed settings", "", "", "", on, false},
		{"a status line here", `{"statusLine": {"type": "command", "command": "x"}, "enabledPlugins": {"` + names.PluginID + `": true}}`, "", "", "", false},
		{"a status line in the project", "", `{"statusLine": {"type": "command", "command": "x"}, "enabledPlugins": {"` + names.PluginID + `": true}}`, "", "", false},
		{"a status line in managed settings", "", on, "", theirs, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root, own, data := sandbox(t)
			local := filepath.Join(root, names.LocalSettings)
			for path, text := range map[string]string{
				local: tc.local,
				filepath.Join(root, names.ProjectSettings):  tc.project,
				filepath.Join(own, "settings.json"):         tc.user,
				filepath.Join(own, "managed-settings.json"): tc.manage,
			} {
				if text != "" {
					write(t, path, text)
				}
			}
			before := contents(t, local)
			shown, err := Sync(root, root, data, true)
			if err != nil || shown != tc.shown {
				t.Fatalf("Sync = %v, %v; want %v", shown, err, tc.shown)
			}
			want := "'" + filepath.Join(data, "baloo") + "' status-line # managed by baloo"
			if got := statusLine(t, local); tc.shown && got != want {
				t.Errorf("%s has status line %q; want %q", local, got, want)
			}
			if got := contents(t, local); !tc.shown && got != before {
				t.Errorf("%s = %q; want it as it was, %q", local, got, before)
			}
		})
	}
}

// The command runs the binary through a link in the data folder, and a second session start
// changes nothing.
func TestSyncLinks(t *testing.T) {
	root, own, data := sandbox(t)
	write(t, filepath.Join(own, "settings.json"), on)
	if _, err := Sync(root, root, data, true); err != nil {
		t.Fatal(err)
	}
	exe, _ := os.Executable()
	if got, err := os.Readlink(filepath.Join(data, "baloo")); err != nil || got != exe {
		t.Errorf("link = %q, %v; want the running binary %q", got, err, exe)
	}
	local := filepath.Join(root, names.LocalSettings)
	before := contents(t, local)
	if shown, err := Sync(root, root, data, true); shown || err != nil || contents(t, local) != before {
		t.Errorf("second Sync = %v, %v, %q; want nothing shown or changed", shown, err, contents(t, local))
	}
	if got := contents(t, filepath.Join(root, ".git", "info", "exclude")); got != "/"+names.LocalSettings+"\n" {
		t.Errorf("info/exclude = %q; want the settings file it created", got)
	}
	if entries, _ := os.ReadDir(data); len(entries) != 1 {
		t.Errorf("data folder has %v; want only the link", entries)
	}
}

// The plugin's own status line, from another data folder, is set again in place, and turned off
// it is taken out, the rest of the file kept; another's is left alone.
func TestSyncOwn(t *testing.T) {
	root, _, data := sandbox(t)
	local := filepath.Join(root, names.LocalSettings)
	old := `{
  "enabledPlugins": {"` + names.PluginID + `": true},
  "statusLine": {"type": "command", "command": "'/old/baloo' status-line # managed by baloo", "padding": 0}
}
`
	write(t, local, old)
	if shown, err := Sync(root, root, data, true); shown || err != nil {
		t.Errorf("Sync over its own = %v, %v; want it set again, not shown", shown, err)
	}
	if got, want := statusLine(t, local), "'"+filepath.Join(data, "baloo")+"' status-line # managed by baloo"; got != want {
		t.Errorf("status line = %q; want %q", got, want)
	}
	if _, err := Sync(root, root, data, false); err != nil {
		t.Fatal(err)
	}
	if got, want := contents(t, local), "{\n  \"enabledPlugins\": {\""+names.PluginID+"\": true}\n}\n"; got != want {
		t.Errorf("turned off, %s = %q; want %q", local, got, want)
	}
	write(t, local, theirs)
	if _, err := Sync(root, root, data, false); err != nil || contents(t, local) != theirs {
		t.Errorf("turned off with another's, %s = %q, %v; want it as it was", local, contents(t, local), err)
	}
}

// Without the data folder the status line can't be set, which is an error only where it would be.
func TestSyncNoData(t *testing.T) {
	root, own, _ := sandbox(t)
	if _, err := Sync(root, root, "", true); err != nil {
		t.Errorf("Sync not enabled = %v; want no error", err)
	}
	write(t, filepath.Join(own, "settings.json"), on)
	if shown, err := Sync(root, root, "", true); shown || err == nil {
		t.Errorf("Sync enabled = %v, %v; want an error", shown, err)
	}
}
