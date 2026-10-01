package checks

import (
	"path/filepath"
	"testing"
)

func TestChangesConfig(t *testing.T) {
	dir := t.TempDir()
	config := filepath.Join(dir, ".claude", "baloo.yml")
	for in, want := range map[string]bool{
		`{"tool_name": "Edit", "tool_input": {"file_path": "` + config + `"}}`:               true,
		`{"tool_name": "Write", "tool_input": {"file_path": ".claude/baloo.yml"}}`:           true,
		`{"tool_name": "MultiEdit", "tool_input": {"file_path": "./.claude/baloo.yml"}}`:     true,
		`{"tool_name": "Edit", "tool_input": {"file_path": "/elsewhere/.claude/baloo.yml"}}`: false,
		`{"tool_name": "Edit", "tool_input": {"file_path": ".claude/settings.json"}}`:        false,
		`{"tool_name": "Read", "tool_input": {"file_path": ".claude/baloo.yml"}}`:            false,
	} {
		if got := ChangesConfig(call(t, in), dir, config); got != want {
			t.Errorf("ChangesConfig(%s) = %v, want %v", in, got, want)
		}
	}
	for command, want := range map[string]bool{
		"sed -i 's/true/false/' .claude/baloo.yml":       true,
		"cd .claude && echo 'git-hooks: {}' > baloo.yml": true,
		"rm .claude/baloo.yml":                           true,
		"git status":                                     false,
	} {
		if got := ChangesConfig(bash(t, command), dir, config); got != want {
			t.Errorf("ChangesConfig(%q) = %v, want %v", command, got, want)
		}
	}
}

func TestTurnsHooksOff(t *testing.T) {
	dir := t.TempDir()
	own := filepath.Join(t.TempDir(), "claude")
	edit := func(tool, path, text string) string {
		return `{"tool_name": "` + tool + `", "tool_input": {"file_path": "` + path + `", ` + text + `}}`
	}
	for in, want := range map[string]bool{
		edit("Edit", ".claude/settings.json", `"new_string": "\"disableAllHooks\": true"`):                true,
		edit("Write", "/home/me/.claude/settings.local.json", `"content": "{\"enabledPlugins\": {}}"`):    true,
		edit("MultiEdit", own+"/settings.json", `"edits": [{"new_string": "\"disableAllHooks\": true"}]`): true,
		edit("Edit", ".claude/settings.json", `"new_string": "\"baloo@bunderlog\": false"`):               true,
		edit("Edit", ".claude/settings.json", `"new_string": "\"permissions\": {}"`):                      false,
		edit("Edit", "config/settings.json", `"new_string": "\"disableAllHooks\": true"`):                 false,
		edit("Edit", ".claude/baloo.yml", `"new_string": "disableAllHooks"`):                              false,
		`{"tool_name": "Read", "tool_input": {"file_path": ".claude/settings.json"}}`:                     false,
	} {
		if got := TurnsHooksOff(call(t, in), dir, own); got != want {
			t.Errorf("TurnsHooksOff(%s) = %v, want %v", in, got, want)
		}
	}
	for command, want := range map[string]bool{
		`jq '.disableAllHooks = true' .claude/settings.json > s && mv s .claude/settings.json`:       true,
		`cd ~/.claude && sed -i 's/"baloo@bunderlog": true/"baloo@bunderlog": false/' settings.json`: true,
		`cd ~/.claude && sed -i 's/true/false/' settings.json # enabledPlugins`:                      true,
		"claude plugin disable baloo@bunderlog":                                                      true,
		"claude plugin uninstall baloo":                                                              true,
		"claude plugin disable other@bunderlog":                                                      false,
		"echo disableAllHooks":                                                                       false,
		"cat .claude/settings.json":                                                                  false,
	} {
		if got := TurnsHooksOff(bash(t, command), dir, own); got != want {
			t.Errorf("TurnsHooksOff(%q) = %v, want %v", command, got, want)
		}
	}
}
