// Package checks holds the Checks, each a function of what git or Claude Code gives the Git hook
// or the Hook that runs it.
package checks

// GitHookChecks are the Checks Git hooks run, by name: each is off without its key in the Config.
var GitHookChecks = []string{"no-ai-coauthor", "conventional-commits", "no-secrets-in-commits",
	"linear-history"}

// ToolCallChecks are the Checks a Hook runs on Claude's tool calls, by name: each is on without its
// key in the Config (ADR checks).
var ToolCallChecks = []string{"no-git-hook-bypass", "no-destructive-commands",
	"no-secrets-in-context"}
