// Package checks holds the Checks, each a function of what git or Claude Code gives the Git hook
// or the Hook that runs it.
package checks

// GitHookChecks are the Checks Git hooks run, by name: each is off without its key under git-hooks
// in the Config.
var GitHookChecks = func() (list []string) {
	for _, c := range gitHookChecks {
		list = append(list, c.name)
	}
	return list
}()

// HookChecks are the Checks a Hook runs, by name: each is on without its key under claude-hooks in
// the Config (ADR checks).
var HookChecks = []string{"no-git-hook-bypass", "no-secrets-in-context"}

// GitHooks are the Git hooks the plugin writes (ADR git-hooks), each with its Checks, in the order
// it runs them.
var GitHooks = func() map[string][]string {
	hooks := map[string][]string{}
	for _, c := range gitHookChecks {
		hooks[c.hook] = append(hooks[c.hook], c.name)
	}
	return hooks
}()
