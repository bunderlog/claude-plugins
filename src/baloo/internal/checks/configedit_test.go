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
		"sed -i 's/true/false/' .claude/baloo.yml":    true,
		"cd .claude && echo 'checks: {}' > baloo.yml": true,
		"rm .claude/baloo.yml":                        true,
		"git status":                                  false,
	} {
		if got := ChangesConfig(bash(t, command), dir, config); got != want {
			t.Errorf("ChangesConfig(%q) = %v, want %v", command, got, want)
		}
	}
}
