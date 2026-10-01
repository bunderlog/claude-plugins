package main

import (
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
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
		Rules: c.CommitRules}, c.CheckOn
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
// Config turns on, and denies the call when one would, else asks the user first when one would,
// and asks too before a change to the Config or one that may turn its Hooks off.
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
	bash := call.Tool == "Bash"
	var ask []string
	if c.CheckOn("no-git-hook-bypass") && bash {
		if why := checks.NoGitHookBypass(call.Input.Command); why != "" {
			return decide(stdout, "deny", names.Plugin+":no-git-hook-bypass: "+why+runItYourself)
		}
	}
	if c.CheckOn("no-destructive-commands") && bash {
		deny, asks := checks.NoDestructiveCommands(call.Input.Command, call.Cwd)
		if deny != "" {
			return decide(stdout, "deny", names.Plugin+":no-destructive-commands: "+deny+runItYourself)
		}
		if asks != "" {
			ask = append(ask, names.Plugin+":no-destructive-commands: "+asks)
		}
	}
	if c.CheckOn("no-secrets-in-context") {
		if why := checks.NoSecretsInContext(call.ToolCall, call.Cwd); why != "" {
			return decide(stdout, "deny", names.Plugin+":no-secrets-in-context: "+why)
		}
	}
	own := filepath.Join(c.Root, names.Config)
	if c.Root != "" && checks.ChangesConfig(call.ToolCall, call.Cwd, own) {
		ask = append(ask, names.Plugin+": this may change "+names.Config+", which turns the plugin's "+
			"checks on and off")
	}
	if checks.TurnsHooksOff(call.ToolCall, call.Cwd, os.Getenv("CLAUDE_CONFIG_DIR")) {
		ask = append(ask, names.Plugin+": this may turn off the hooks that run the plugin's checks")
	}
	if len(ask) > 0 {
		return decide(stdout, "ask", strings.Join(ask, "; "))
	}
	return 0
}

// decide prints a PreToolUse Hook's `decision`, deny or ask, with its reason, for Claude Code.
func decide(stdout io.Writer, decision, reason string) int {
	out := json.NewEncoder(stdout)
	out.SetEscapeHTML(false)
	out.Encode(map[string]any{"hookSpecificOutput": map[string]string{
		"hookEventName":            "PreToolUse",
		"permissionDecision":       decision,
		"permissionDecisionReason": reason,
	}})
	return 0
}
