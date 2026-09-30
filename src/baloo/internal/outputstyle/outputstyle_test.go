package outputstyle

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// sandbox is a temporary repo with the user's and the managed settings of its own, none of them
// there yet; it returns the repo's root and Claude Code's own folder.
func sandbox(t *testing.T) (root, own string) {
	t.Helper()
	root, own = t.TempDir(), t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CLAUDE_CONFIG_DIR", own)
	t.Setenv("BALOO_MANAGED_SETTINGS", filepath.Join(own, "managed-settings.json"))
	return root, own
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

const on = `{"enabledPlugins": {"` + names.PluginID + `": true}}`
const off = `{"enabledPlugins": {"` + names.PluginID + `": false}}`

func TestPick(t *testing.T) {
	const local, project = names.LocalSettings, names.ProjectSettings
	for _, tc := range []struct {
		name                         string
		local, project, user, manage string
		// where is the settings file it writes, or "" for none.
		where string
	}{
		{"enabled in the project", "", on, "", "", project},
		{"enabled in the project, an empty file here", " \n", on, "", "", project},
		{"enabled here", on, "", "", "", local},
		{"enabled for the user", "", "", on, "", local},
		{"enabled here and in the project", on, on, "", "", local},
		{"enabled in the project and for the user", "", on, on, "", project},
		{"not enabled anywhere", "", "", "", "", ""},
		{"enabled only by managed settings", "", "", "", on, ""},
		{"another plugin enabled", "", `{"enabledPlugins": {"x@y": true}}`, "", "", ""},
		{"turned off here, on for the user", off, "", on, "", ""},
		{"turned off in the project, on for the user", "", off, on, "", ""},
		{"turned on here, off in the project", on, off, "", "", local},
		{"a style set here", `{"outputStyle": "Explanatory"}`, on, "", "", ""},
		{"a style set in the project", "", `{"outputStyle": "x", "enabledPlugins": {"` + names.PluginID + `": true}}`, "", "", ""},
		{"the default style set for the user", "", on, `{"outputStyle": "default"}`, "", ""},
		{"a style set by managed settings", "", on, "", `{"outputStyle": "x"}`, ""},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root, own := sandbox(t)
			for path, text := range map[string]string{
				filepath.Join(root, local):                  tc.local,
				filepath.Join(root, project):                tc.project,
				filepath.Join(own, "settings.json"):         tc.user,
				filepath.Join(own, "managed-settings.json"): tc.manage,
			} {
				if text != "" {
					write(t, path, text)
				}
			}
			got, err := Pick(root, root, "short-replies")
			if err != nil {
				t.Fatal(err)
			}
			want := ""
			if tc.where != "" {
				want = filepath.Join(root, tc.where)
			}
			if got.Path != want {
				t.Fatalf("Pick = %+v; want %q", got, want)
			}
			for _, file := range []string{local, project} {
				var fields map[string]any
				path := filepath.Join(root, file)
				if text := contents(t, path); strings.TrimSpace(text) != "" {
					if err := json.Unmarshal([]byte(text), &fields); err != nil {
						t.Fatalf("%s is not JSON: %v\n%s", path, err, text)
					}
				}
				style, _ := fields["outputStyle"].(string)
				if written := style == "baloo:short-replies"; written != (file == tc.where) {
					t.Errorf("%s has outputStyle %q; want baloo:short-replies only in %q", file, style, tc.where)
				}
			}
		})
	}
}

// A settings file that was there keeps the rest of its text as it was.
func TestPickKeepsTheFile(t *testing.T) {
	root, _ := sandbox(t)
	local := filepath.Join(root, names.LocalSettings)
	text := "{\n  \"enabledPlugins\": {\n    \"" + names.PluginID + "\": true\n  }\n}\n"
	write(t, local, text)
	if _, err := Pick(root, root, "short-replies"); err != nil {
		t.Fatal(err)
	}
	want := "{\n  \"outputStyle\": \"baloo:short-replies\",\n" + text[2:]
	if got := contents(t, local); got != want {
		t.Errorf("%s = %q; want %q", local, got, want)
	}
	if got := contents(t, filepath.Join(root, ".git", "info", "exclude")); got != "" {
		t.Errorf("info/exclude = %q for a file that was there; want nothing", got)
	}
}

// With the plugin enabled for the user, the settings.local.json it creates goes into info/exclude
// once, even for a worktree, whose info/ is the one its repo's worktrees share.
func TestPickExcludes(t *testing.T) {
	root, own := sandbox(t)
	write(t, filepath.Join(own, "settings.json"), on)
	exclude := filepath.Join(root, ".git", "info", "exclude")
	write(t, exclude, "# git's own comment")
	for range 2 {
		os.Remove(filepath.Join(root, names.LocalSettings))
		if _, err := Pick(root, root, "short-replies"); err != nil {
			t.Fatal(err)
		}
	}
	if got, want := contents(t, exclude), "# git's own comment\n/"+names.LocalSettings+"\n"; got != want {
		t.Errorf("info/exclude = %q; want %q", got, want)
	}

	main, own := sandbox(t)
	write(t, filepath.Join(own, "settings.json"), on)
	tree := t.TempDir()
	gitdir := filepath.Join(main, ".git", "worktrees", "tree")
	write(t, filepath.Join(gitdir, "commondir"), "../..\n")
	write(t, filepath.Join(tree, ".git"), "gitdir: "+gitdir+"\n")
	if _, err := Pick(tree, tree, "short-replies"); err != nil {
		t.Fatal(err)
	}
	if got := contents(t, filepath.Join(main, ".git", "info", "exclude")); got != "/"+names.LocalSettings+"\n" {
		t.Errorf("the repo's info/exclude = %q; want the worktree's settings file", got)
	}
}

// A settings file that isn't JSON is a problem, and nothing is written.
func TestPickBadSettings(t *testing.T) {
	root, _ := sandbox(t)
	project := filepath.Join(root, names.ProjectSettings)
	write(t, project, "{nope")
	if got, err := Pick(root, root, "short-replies"); got.Path != "" || err == nil || !strings.Contains(err.Error(), project) {
		t.Errorf("Pick with a broken %s = %q, %v; want nothing and an error naming it", project, got, err)
	}
	local := filepath.Join(root, names.LocalSettings)
	write(t, project, on)
	write(t, local, "[]")
	if got, err := Pick(root, root, "short-replies"); got.Path != "" || err == nil {
		t.Errorf("Pick with a list in %s = %q, %v; want nothing and an error", local, got, err)
	}
	if got := contents(t, local); got != "[]" {
		t.Errorf("%s = %q; want it as it was", local, got)
	}
}

// Picked names the Scope that enables the plugin, which may not be the file's.
func TestPickScope(t *testing.T) {
	for scope, file := range map[settings.Scope]string{settings.Local: names.LocalSettings, settings.Project: names.ProjectSettings, settings.User: ""} {
		root, own := sandbox(t)
		if file == "" {
			write(t, filepath.Join(own, "settings.json"), on)
		} else {
			write(t, filepath.Join(root, file), on)
		}
		got, err := Pick(root, root, "short-replies")
		if err != nil || got.Enabled != scope {
			t.Errorf("Pick enabled by %s = %+v, %v; want Enabled %s", scope, got, err, scope)
		}
	}
}
