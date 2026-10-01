// cspell:ignore fgrep

package checks

import (
	"path/filepath"
	"slices"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// ChangesConfig says whether the tool call `call`, run in the folder `dir`, may change the Config
// at the path `config`, for Claude to ask the user first (ADR checks): an Edit, Write or MultiEdit
// of it, or a Bash command that names a file of its name, unless only a program of readOnly reads it.
func ChangesConfig(call ToolCall, dir, config string) bool {
	switch call.Tool {
	case "Edit", "Write", "MultiEdit":
		path := call.Input.FilePath
		if !filepath.IsAbs(path) {
			path = filepath.Join(dir, path)
		}
		return filepath.Clean(path) == filepath.Clean(config)
	case "Bash":
		for _, p := range programs(call.Input.Command) {
			for i, w := range p.args {
				if filepath.Base(strings.TrimLeft(w, "<>")) != filepath.Base(config) {
					continue
				}
				redirected := strings.Contains(w, ">") || i > 0 && strings.HasSuffix(p.args[i-1], ">")
				if redirected || !reads(p) {
					return true
				}
			}
		}
	}
	return false
}

// readOnly are programs that only read the files they name; sed is one without -i.
var readOnly = []string{"cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "wc",
	"diff", "ls", "stat", "file", "jq", "sed"}

// gitReaders are git's subcommands that only read the files they name.
var gitReaders = []string{"diff", "log", "show", "blame", "ls-files", "status", "grep"}

// reads says whether the program `p` only reads the files it names.
func reads(p program) bool {
	switch p.name {
	case "git":
		_, sub, _ := splitGit(p.args)
		return slices.Contains(gitReaders, sub)
	case "sed":
		return !hasFlag(p.args, "-i") && !slices.ContainsFunc(p.args, func(a string) bool {
			return strings.HasPrefix(a, "--in-place")
		})
	}
	return slices.Contains(readOnly, p.name)
}

// hookKeys are what a change to Claude Code's settings names to turn the plugin's Hooks off:
// every Hook, every plugin's setting, or the plugin's own.
var hookKeys = []string{"disableAllHooks", "enabledPlugins", names.Plugin + "@"}

// TurnsHooksOff says whether the tool call `call`, run in the folder `dir`, may turn off the Hooks
// that run the Hook Checks, for Claude to ask the user first (ADR checks): an Edit, Write or
// MultiEdit of a settings file of Claude Code's whose new text names a key of hookKeys, a Bash
// command that names such a file and such a key, or `claude plugin disable` or `uninstall` of the
// plugin. Claude Code's own folder is `claudeDir`, or a .claude folder when "".
func TurnsHooksOff(call ToolCall, dir, claudeDir string) bool {
	namesKey := func(text string) bool {
		return slices.ContainsFunc(hookKeys, func(k string) bool { return strings.Contains(text, k) })
	}
	in := call.Input
	switch call.Tool {
	case "Edit", "Write", "MultiEdit":
		path := in.FilePath
		if !filepath.IsAbs(path) {
			path = filepath.Join(dir, path)
		}
		written := in.Content + in.NewString
		for _, e := range in.Edits {
			written += e.NewString
		}
		return settingsFile(path, claudeDir) && namesKey(written)
	case "Bash":
		settings := false
		for _, words := range split(in.Command) {
			if len(words) >= 4 && filepath.Base(words[0]) == "claude" && words[1] == "plugin" &&
				(words[2] == "disable" || words[2] == "uninstall") &&
				slices.ContainsFunc(words[3:], plugin) {
				return true
			}
			for _, w := range words {
				settings = settings || settingsName(filepath.Base(strings.TrimLeft(w, "<>")))
			}
		}
		return settings && namesKey(in.Command)
	}
	return false
}

// plugin says whether the word `w` names the plugin, alone or with its marketplace.
func plugin(w string) bool { return w == names.Plugin || strings.HasPrefix(w, names.Plugin+"@") }

// settingsName says whether `name` is the name of a settings file of Claude Code's.
func settingsName(name string) bool {
	return name == filepath.Base(names.ProjectSettings) || name == filepath.Base(names.LocalSettings)
}

// settingsFile says whether `path` is a settings file of Claude Code's: one in a .claude folder,
// or in `claudeDir`.
func settingsFile(path, claudeDir string) bool {
	parent := filepath.Dir(path)
	return settingsName(filepath.Base(path)) &&
		(filepath.Base(parent) == ".claude" || claudeDir != "" && parent == filepath.Clean(claudeDir))
}
