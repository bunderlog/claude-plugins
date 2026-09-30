package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// commitMessage are the commit-msg Git hook's Checks, by name: each says what is wrong with a
// commit message under the Config `c`, or "" when nothing is.
var commitMessage = map[string]func(message string, c config.Config) string{
	"no-ai-coauthor": func(message string, _ config.Config) string {
		if found := checks.NoAICoauthor(message); len(found) > 0 {
			return "remove the AI co-author or credit:\n" + strings.Join(found, "\n")
		}
		return ""
	},
	"conventional-commits": func(message string, c config.Config) string {
		return checks.ConventionalCommit(message, c.CommitRules)
	},
}

// check runs a Git hook's Check `name` with the arguments `args`, in the repo git runs it in, and
// returns its exit code for git; not ok when there is no such Check or it takes other arguments.
// A Check the repo's Config turns off passes everything (ADR checks).
func check(name string, args []string, stdin io.Reader, stderr io.Writer) (code int, ok bool) {
	run := map[string]func() int{
		"no-secrets-in-commits": func() int { return noSecretsInCommits(stderr) },
		"no-stale-adr-date":     func() int { return noStaleADRDate(stderr) },
		"linear-history":        func() int { return linearHistory(stdin, stderr) },
	}[name]
	if commitMessage[name] != nil && len(args) == 1 {
		run = func() int { return checkCommitMessage(name, args[0], stderr) }
	} else if len(args) != 0 {
		run = nil
	}
	if run == nil {
		return 0, false
	}
	if dir, err := os.Getwd(); err != nil || !config.Read(dir).CheckOn(name) {
		return 0, true
	}
	return run(), true
}

// checkCommitMessage runs the commit-msg Check `name` on the message in the file `path`: it fails
// with what is wrong, for git to show.
func checkCommitMessage(name, path string, stderr io.Writer) int {
	message, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(stderr, "%s:%s: %v\n", names.Plugin, name, err)
		return 2
	}
	dir, _ := os.Getwd()
	why := commitMessage[name](string(message), config.Read(dir))
	if why == "" {
		return 0
	}
	fmt.Fprintf(stderr, "%s:%s: %s\n", names.Plugin, name, why)
	return 1
}

// noSecretsInCommits is the pre-commit Git hook's Check baloo:no-secrets-in-commits on the repo git
// runs it in: it fails with where each Secret the staged changes add is, for git to show, but
// never the Secret.
func noSecretsInCommits(stderr io.Writer) int {
	const name = names.Plugin + ":no-secrets-in-commits"
	found, err := checks.NoSecretsInCommits(".")
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", name, err)
		return 2
	}
	if len(found) == 0 {
		return 0
	}
	fmt.Fprintf(stderr, "%s: remove each secret, or mark a false alarm with %s:\n%s\n",
		name, checks.AllowSecret, strings.Join(found, "\n"))
	return 1
}

// noStaleADRDate is the pre-commit Git hook's Check baloo:no-stale-adr-date on the repo git runs it
// in: it fails with each accepted ADR the staged changes change without dating it today.
func noStaleADRDate(stderr io.Writer) int {
	const name = names.Plugin + ":no-stale-adr-date"
	found, err := checks.NoStaleADRDate(".", time.Now().Format(time.DateOnly))
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", name, err)
		return 2
	}
	if len(found) == 0 {
		return 0
	}
	fmt.Fprintf(stderr, "%s: an ADR's Date is when it last changed:\n%s\n", name,
		strings.Join(found, "\n"))
	return 1
}

// linearHistory is the pre-push Git hook's Check baloo:linear-history on the repo git runs it in:
// it fails with the merge commits the push sends, from the refs git gives it on stdin.
func linearHistory(stdin io.Reader, stderr io.Writer) int {
	const name = names.Plugin + ":linear-history"
	pushed, err := io.ReadAll(stdin)
	var found []string
	if err == nil {
		found, err = checks.LinearHistory(".", string(pushed))
	}
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", name, err)
		return 2
	}
	if len(found) == 0 {
		return 0
	}
	fmt.Fprintf(stderr, "%s: rebase instead of merging, then push the rebased branch with "+
		"--force-with-lease; merge commits:\n%s\n", name, strings.Join(found, "\n"))
	return 1
}

// runItYourself ends the reason of a command denied, for Claude to leave it to the user.
const runItYourself = ". If it's really needed, ask the user to run it themselves with " +
	"`! <command>`."

// hookCall is the tool call Claude Code gives a PreToolUse hook, with the folder it runs in.
type hookCall struct {
	checks.ToolCall
	Cwd string `json:"cwd"`
}

// preToolUse is the PreToolUse Hook on Claude's tool calls (ADR checks): it runs the Checks on
// them that the Config turns on, and denies the call when one would, else asks the user first
// when one would, and asks too before a change to the Config or one that may turn its Hooks off.
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
