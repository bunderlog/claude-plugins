package checks

import (
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Input is what the Checks Git hooks run read besides git's arguments: the repo, git's stdin,
// today's date and conventional-commits' settings.
type Input struct {
	Dir   string
	Stdin io.Reader
	Today string // YYYY-MM-DD
	Rules CommitRules
}

// gitHookCheck is a Check a Git hook runs: what it finds in the Input and the one argument it
// takes, if any, and what it tells the user to do about it.
type gitHookCheck struct {
	name, hook string
	arg        string // the argument it takes, "" for none
	stdin      string // what it reads on stdin, "" for nothing
	advice     string // the line before what it found, "" to show that alone
	find       func(in Input, arg string) ([]string, error)
}

// gitHookChecks are the Checks Git hooks run, in the order each Git hook runs its own.
var gitHookChecks = []gitHookCheck{
	{name: "no-ai-coauthor", hook: "commit-msg", arg: "<message file>",
		advice: "remove the AI co-author or credit",
		find: func(_ Input, path string) ([]string, error) {
			message, err := os.ReadFile(path)
			return NoAICoauthor(string(message)), err
		}},
	{name: "conventional-commits", hook: "commit-msg", arg: "<message file>",
		find: func(in Input, path string) ([]string, error) {
			message, err := os.ReadFile(path)
			if err != nil {
				return nil, err
			}
			if why := ConventionalCommit(string(message), in.Rules); why != "" {
				return []string{why}, nil
			}
			return nil, nil
		}},
	{name: "no-secrets-in-commits", hook: "pre-commit",
		advice: "remove each secret, or mark a false alarm with " + AllowSecret,
		find:   func(in Input, _ string) ([]string, error) { return NoSecretsInCommits(in.Dir) }},
	{name: "no-stale-adr-date", hook: "pre-commit",
		advice: "an ADR's Date is when it last changed",
		find:   func(in Input, _ string) ([]string, error) { return NoStaleADRDate(in.Dir, in.Today) }},
	{name: "linear-history", hook: "pre-push", stdin: "<pushed refs>",
		advice: "rebase instead of merging, then push the rebased branch with --force-with-lease; " +
			"git config pull.rebase true makes git pull rebase; merge commits",
		find: func(in Input, _ string) ([]string, error) {
			pushed, err := io.ReadAll(in.Stdin)
			if err != nil {
				return nil, err
			}
			return LinearHistory(in.Dir, string(pushed))
		}},
}

// Run runs the Check `name` a Git hook runs with git's arguments `args`, when `on` says the Config
// turns it on, and returns its exit code for git: 0 when it finds nothing or is off, 1 with what it
// found on `stderr`, 2 with why it couldn't check. Not ok when there is no such Check, or `args`
// aren't the ones it takes.
func Run(name string, args []string, in Input, on func(name string) bool, stderr io.Writer) (code int, ok bool) {
	for _, c := range gitHookChecks {
		if c.name != name {
			continue
		}
		if (c.arg == "") != (len(args) == 0) || len(args) > 1 {
			return 0, false
		}
		if !on(name) {
			return 0, true
		}
		arg := ""
		if len(args) == 1 {
			arg = args[0]
		}
		found, err := c.find(in, arg)
		prefix := names.Plugin + ":" + name + ": "
		switch {
		case err != nil:
			fmt.Fprintf(stderr, "%s%v\n", prefix, err)
			return 2, true
		case len(found) == 0:
			return 0, true
		case c.advice != "":
			prefix += c.advice + ":\n"
		}
		fmt.Fprintf(stderr, "%s%s\n", prefix, strings.Join(found, "\n"))
		return 1, true
	}
	return 0, false
}

// RunHook runs the Checks of the Git hook `hook` (ADR git-hooks) that `on` turns on, all of them,
// each with the first of git's arguments `args` if it takes one, and returns the worst of their exit
// codes. Not ok when the plugin writes no such Git hook, or git gives none of the arguments one of
// its Checks takes.
func RunHook(hook string, args []string, in Input, on func(name string) bool, stderr io.Writer) (code int, ok bool) {
	if _, ok := GitHooks[hook]; !ok {
		return 0, false
	}
	var own [][]string
	for _, c := range gitHookChecks {
		switch {
		case c.hook != hook:
			continue
		case c.arg == "":
			own = append(own, nil)
		case len(args) == 0:
			return 0, false
		default:
			own = append(own, args[:1])
		}
	}
	for i, name := range GitHooks[hook] {
		c, ok := Run(name, own[i], in, on, stderr)
		if !ok { // the registry and Run disagree: fail rather than skip the Check
			fmt.Fprintf(stderr, "%s:%s: could not run it\n", names.Plugin, name)
			c = 2
		}
		code = max(code, c)
	}
	return code, true
}

// Usage is how to run each Check a Git hook runs by hand, one line each: `check <name>` with the
// argument it takes or what it reads on stdin.
func Usage() []string {
	var lines []string
	for _, c := range gitHookChecks {
		line := "check " + c.name
		if c.arg != "" {
			line += " " + c.arg
		}
		if c.stdin != "" {
			line += " < " + c.stdin
		}
		lines = append(lines, line)
	}
	return lines
}
