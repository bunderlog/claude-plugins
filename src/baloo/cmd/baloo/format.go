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
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
)

// formatTimeout is how long the command may run, under the Hook's own limit.
const formatTimeout = 50 * time.Second

// postToolUse is the PostToolUse Hook on Claude's edits (ADR format-on-edit): it runs the Config's
// format-on-edit command in the repo's root on the file an Edit, Write or MultiEdit changed, when
// it is in the repo. It says nothing, whatever the command does: the Stop check reports failures.
func postToolUse(stdin io.Reader) int {
	var call struct {
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
	if c.Root == "" || c.FormatOnEdit == "" || err != nil || rel == ".." ||
		strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return 0
	}
	ctx, cancel := context.WithTimeout(context.Background(), formatTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "sh", "-c", c.FormatOnEdit+` "$1"`, "sh", rel)
	cmd.Dir = c.Root
	cmd.Run()
	return 0
}
