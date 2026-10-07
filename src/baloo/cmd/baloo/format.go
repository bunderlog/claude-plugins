package main

import (
	"context"
	"encoding/json"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// formatTimeout is how long the command may run, under the Hook's own limit.
const formatTimeout = 50 * time.Second

// postToolUse is the PostToolUse Hook on Claude's reads and edits. For a file in the repo, it gives
// Claude the Guidelines whose subject the file is, once a session (ADR guidelines), and after an
// Edit, Write or MultiEdit it runs the Config's format-on-edit command in the repo's root on the
// file (ADR format-on-edit), saying nothing of how that went. In a Session review's session it
// does nothing.
func postToolUse(stdin io.Reader, stdout io.Writer) int {
	var call struct {
		Session   string `json:"session_id"`
		Tool      string `json:"tool_name"`
		ToolInput struct {
			FilePath string `json:"file_path"`
		} `json:"tool_input"`
	}
	dir, err := project()
	if os.Getenv(review.Env) != "" || err != nil || json.NewDecoder(stdin).Decode(&call) != nil {
		return 0
	}
	c := config.Read(dir)
	rel, err := filepath.Rel(c.Root, call.ToolInput.FilePath)
	if c.Root == "" || err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return 0
	}
	given, _ := guidelines.ForFile(os.Getenv("CLAUDE_PLUGIN_ROOT"), os.Getenv("CLAUDE_PLUGIN_DATA"),
		call.Session, rel, c.Guidelines)
	if given != "" {
		out := json.NewEncoder(stdout)
		out.SetEscapeHTML(false)
		out.Encode(map[string]any{"hookSpecificOutput": map[string]string{
			"hookEventName":     "PostToolUse",
			"additionalContext": names.Plugin + ":\n" + given + "\n",
		}})
	}
	if c.FormatOnEdit == "" || call.Tool == "Read" {
		return 0
	}
	ctx, cancel := context.WithTimeout(context.Background(), formatTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "sh", "-c", c.FormatOnEdit+` "$1"`, "sh", rel)
	cmd.Dir = c.Root
	cmd.Run()
	return 0
}
