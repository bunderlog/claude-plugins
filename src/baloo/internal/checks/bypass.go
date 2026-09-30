package checks

import (
	"slices"
	"strings"
)

// NoGitHookBypass is the Check baloo:no-git-hook-bypass (PreToolUse on Bash): why the shell
// command `command` would bypass the Git hooks, or "" when it wouldn't. That is `--no-verify` on
// any git subcommand, `-n` on commit, core.hooksPath set for one command or written to git's
// config, and HUSKY=0, which turns off husky and the Git hooks it runs.
func NoGitHookBypass(command string) string {
	for _, p := range programs(command) {
		if slices.Contains(p.env, "HUSKY=0") || p.name == "export" && slices.Contains(p.args, "HUSKY=0") {
			return "HUSKY=0 turns the Git hooks off"
		}
		if p.name != "git" {
			continue
		}
		options, sub, rest := splitGit(p.args)
		for i, option := range options {
			v, env := strings.CutPrefix(option, "--config-env=")
			if env && hooksPath(v) || option == "-c" && i+1 < len(options) && hooksPath(options[i+1]) {
				return "git -c core.hooksPath=… bypasses the Git hooks"
			}
		}
		if slices.Contains(rest, "--no-verify") || sub == "commit" && hasFlag(rest, "-n") {
			return "git " + sub + " --no-verify bypasses the Git hooks"
		}
		if sub == "config" && writesHooksPath(rest) {
			return "git config core.hooksPath changes where the Git hooks are"
		}
	}
	return ""
}

// hooksPath says whether `setting`, `key=value` or a key alone, is core.hooksPath.
func hooksPath(setting string) bool {
	key, _, _ := strings.Cut(setting, "=")
	return strings.EqualFold(key, "core.hooksPath")
}

// writesHooksPath says whether `git config` with the arguments `args` writes or removes
// core.hooksPath, rather than reads it.
func writesHooksPath(args []string) bool {
	var words []string
	writes := false
	for _, a := range args {
		switch {
		case a == "--unset" || a == "--unset-all" || a == "--add" || a == "--replace-all":
			writes = true
		case !strings.HasPrefix(a, "-"):
			words = append(words, a)
		}
	}
	if len(words) > 0 && (words[0] == "set" || words[0] == "unset") {
		words, writes = words[1:], true
	}
	if len(words) == 0 || !hooksPath(words[0]) {
		return false
	}
	return writes || len(words) > 1
}
