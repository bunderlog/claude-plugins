// Package checks holds the Checks, each a function of what git or Claude Code gives the Git hook
// or the Hook that runs it.
package checks

// GitHookChecks are the Checks Git hooks run, by name: each is off without its key under git-hooks
// in the Config.
var GitHookChecks = []string{"no-ai-coauthor", "conventional-commits", "no-secrets-in-commits",
	"no-stale-adr-date", "linear-history"}

// HookChecks are the Checks a Hook runs, by name: each is on without its key under claude-hooks in
// the Config (ADR checks).
var HookChecks = []string{"no-git-hook-bypass", "no-destructive-commands",
	"no-secrets-in-context"}
