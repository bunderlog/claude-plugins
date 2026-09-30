package checks

import (
	"path/filepath"
	"strings"
)

// ChangesConfig says whether the tool call `call`, run in the folder `dir`, may change the Config
// at the path `config`, for Claude to ask the user first (ADR checks): an Edit, Write or MultiEdit
// of it, or a Bash command that names a file of its name.
func ChangesConfig(call ToolCall, dir, config string) bool {
	switch call.Tool {
	case "Edit", "Write", "MultiEdit":
		path := call.Input.FilePath
		if !filepath.IsAbs(path) {
			path = filepath.Join(dir, path)
		}
		return filepath.Clean(path) == filepath.Clean(config)
	case "Bash":
		for _, words := range split(call.Input.Command) {
			for _, w := range words {
				if filepath.Base(strings.TrimLeft(w, "<>")) == filepath.Base(config) {
					return true
				}
			}
		}
	}
	return false
}
