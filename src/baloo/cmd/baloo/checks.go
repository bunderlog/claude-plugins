package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// gitHookInput is what the Checks Git hooks run read in the repo git runs them in, with its
// Config; a Check passes everything, and no command runs, where the Config can't be read.
func gitHookInput(stdin io.Reader) (checks.Input, config.Config) {
	var c config.Config
	if dir, err := os.Getwd(); err == nil {
		c = config.Read(dir)
	}
	return checks.Input{Dir: ".", Stdin: stdin, Today: time.Now().Format(time.DateOnly),
		Rules: c.CommitRules, MaxFileKB: c.MaxFileKB}, c
}

// gitHook runs the Git hook `hook` (ADR git-hooks): its Checks the Config turns on, then, once they
// all pass, the command the Config sets for it, with sh, git's arguments `args` as $1 on, and for
// pre-push the refs git gave on `stdin`, which linear-history reads too. It returns the exit code
// for git: the Checks', or 1 where the command fails. Not ok where the plugin writes no such Git
// hook, or git gives none of the arguments one of its Checks takes.
func gitHook(hook string, args []string, stdin io.Reader, stdout, stderr io.Writer) (int, bool) {
	in, c := gitHookInput(stdin)
	command := c.GitHookCommands[hook]
	if hook == "pre-push" && command != "" {
		pushed, err := io.ReadAll(stdin)
		if err != nil {
			fmt.Fprintf(stderr, "%s:%s.%s: %v\n", names.Plugin, names.GitHookCommands, hook, err)
			return 2, true
		}
		in.Stdin, stdin = bytes.NewReader(pushed), bytes.NewReader(pushed)
	}
	code, ok := checks.RunHook(hook, args, in, c.CheckOn, stderr)
	if !ok || code != 0 || command == "" {
		return code, ok
	}
	cmd := exec.Command("sh", append([]string{"-c", command, "sh"}, args...)...)
	cmd.Stdin, cmd.Stdout, cmd.Stderr = stdin, stdout, stderr
	if err := cmd.Run(); err != nil {
		fmt.Fprintf(stderr, "%s:%s.%s: %s: %v\n", names.Plugin, names.GitHookCommands, hook, command, err)
		return 1, true
	}
	return 0, true
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
