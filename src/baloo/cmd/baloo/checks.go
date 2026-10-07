package main

import (
	"encoding/json"
	"io"
	"os"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// gitHookInput is what the Checks Git hooks run read in the repo git runs them in, with the
// Checks its Config turns on; a Check passes everything where the Config can't be read.
func gitHookInput(stdin io.Reader) (checks.Input, func(name string) bool) {
	var c config.Config
	if dir, err := os.Getwd(); err == nil {
		c = config.Read(dir)
	}
	return checks.Input{Dir: ".", Stdin: stdin, Today: time.Now().Format(time.DateOnly),
		Rules: c.CommitRules, MaxFileKB: c.MaxFileKB}, c.CheckOn
}

// runItYourself ends the reason of a command denied, for Claude to leave it to the user.
const runItYourself = ". If it's really needed, ask the user to run it themselves with " +
	"`! <command>`."

// hookCall is the tool call Claude Code gives a PreToolUse Hook, with the folder it runs in.
type hookCall struct {
	checks.ToolCall
	Cwd string `json:"cwd"`
}

// preToolUse is the PreToolUse Hook of the Checks a Hook runs (ADR checks): it runs the ones the
// Config turns on, and denies the call when one would.
// It says nothing of input it can't read, and Claude Code runs the call as usual.
func preToolUse(stdin io.Reader, stdout io.Writer) int {
	var call hookCall
	dir, err := project()
	if json.NewDecoder(stdin).Decode(&call) != nil || err != nil {
		return 0
	}
	if call.Cwd == "" {
		call.Cwd = dir
	}
	c := config.Read(dir)
	if c.CheckOn("no-git-hook-bypass") && call.Tool == "Bash" {
		if why := checks.NoGitHookBypass(call.Input.Command); why != "" {
			return deny(stdout, names.Plugin+":no-git-hook-bypass: "+why+runItYourself)
		}
	}
	if c.CheckOn("no-secrets-in-context") {
		if why := checks.NoSecretsInContext(call.ToolCall, call.Cwd); why != "" {
			return deny(stdout, names.Plugin+":no-secrets-in-context: "+why)
		}
	}
	return 0
}

// deny prints a PreToolUse Hook's denial, with its reason, for Claude Code.
func deny(stdout io.Writer, reason string) int {
	out := json.NewEncoder(stdout)
	out.SetEscapeHTML(false)
	out.Encode(map[string]any{"hookSpecificOutput": map[string]string{
		"hookEventName":            "PreToolUse",
		"permissionDecision":       "deny",
		"permissionDecisionReason": reason,
	}})
	return 0
}
