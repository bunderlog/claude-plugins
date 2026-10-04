// Package config reads a repo's Config, .claude/baloo.yml, and writes a new one (ADR config). A
// Config that is wrong in part still applies in part: each wrong setting is a problem, one line
// for Claude, and its default applies, so a mistake never stops a Check.
package config

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"go.yaml.in/yaml/v3"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/statusline"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Config is a repo's settings. What a new key needs is in ADR config's Consequences; a Check also
// needs its name in HookChecks, or a Git hook's Check its entry in the checks package's registry.
type Config struct {
	// Root is the root of the repo whose Config this is, or "" where the repo has none (see
	// Load).
	Root string
	// OutputStyle is the plugin's Output style that session start picks where Claude Code's
	// settings pick none (ADR output-styles), or "" for none.
	OutputStyle string
	// StatusLine says whether session start sets the plugin's Status line or takes it out (ADR
	// status-line), or is nil where the Config doesn't say, and the line is left as it is.
	StatusLine *bool
	// StatusLayout is the Status line's bars, their order and thresholds, or nil where the Config
	// sets none and statusline.Default applies.
	StatusLayout *statusline.Layout
	// SessionReview says whether a Session review starts when a session ends (ADR
	// session-review).
	SessionReview bool
	// StopCheck is the command the Stop check runs, or "" where it is off (ADR stop-check).
	StopCheck string
	// FormatOnEdit is the command run on each file Claude edits, or "" where it is off (ADR
	// format-on-edit).
	FormatOnEdit string
	// Guidelines are the Guidelines turned on, by name (ADR guidelines).
	Guidelines map[string]bool
	// Checks are the Checks the Config turns on or off, by name; see CheckOn for one it doesn't.
	Checks map[string]bool
	// CommitRules are conventional-commits' settings.
	CommitRules checks.CommitRules
	// MaxFileKB is no-large-files' limit, in KB, or 0 for its default.
	MaxFileKB int
}

// CheckOn says whether the Check `name` is on: as the Config says, and else on for a Check a Hook
// runs, off for a Git hook's (ADR checks).
func (c Config) CheckOn(name string) bool {
	if on, ok := c.Checks[name]; ok {
		return on
	}
	return slices.Contains(checks.HookChecks, name)
}

// OutputStyles are the plugin's Output styles, the files in its output-styles/.
var OutputStyles = []string{"short-replies"}

// keys decodes each setting's value into a Config, and returns what is wrong with it, a problem
// per line (see at); a key that isn't here is not a setting.
var keys = map[string]func(c *Config, key, value *yaml.Node) []string{
	"output-style": func(c *Config, key, value *yaml.Node) []string {
		var off bool
		if value.Tag == "!!bool" && value.Decode(&off) == nil && !off {
			c.OutputStyle = ""
			return nil
		}
		if value.Tag != "!!str" || !slices.Contains(OutputStyles, value.Value) {
			why := "is not false or one of " + strings.Join(OutputStyles, ", ")
			return []string{wrong(key.Line, key.Value, why)}
		}
		c.OutputStyle = value.Value
		return nil
	},
	"status-line": func(c *Config, key, value *yaml.Node) []string {
		var on bool
		if value.Kind == yaml.MappingNode {
			on = true
			c.StatusLine = &on
			layout, problems := statusLayout(key.Value, value)
			c.StatusLayout = &layout
			return problems
		}
		if value.Tag != "!!bool" || value.Decode(&on) != nil {
			why := ": is not true, false or its bars and thresholds; the Status line is left as it is"
			return []string{at(key.Line, key.Value+why)}
		}
		c.StatusLine = &on
		return nil
	},
	"session-review": func(c *Config, key, value *yaml.Node) []string {
		if value.Tag != "!!bool" || value.Decode(&c.SessionReview) != nil {
			return []string{wrong(key.Line, key.Value, "is not true or false")}
		}
		return nil
	},
	"stop-check":     command(func(c *Config) *string { return &c.StopCheck }),
	"format-on-edit": command(func(c *Config) *string { return &c.FormatOnEdit }),
	"claude-hooks":   checkKeys(checks.HookChecks),
	"git-hooks":      checkKeys(checks.GitHookChecks),
	"guidelines": func(c *Config, key, value *yaml.Node) []string {
		if value.Tag == "!!null" {
			return nil
		}
		if value.Kind != yaml.MappingNode {
			why := "is not a map of guidelines to true or false"
			return []string{wrong(key.Line, key.Value, why)}
		}
		c.Guidelines = map[string]bool{}
		var problems []string
		for i := 0; i+1 < len(value.Content); i += 2 {
			name, on := value.Content[i], value.Content[i+1]
			entry := key.Value + "." + name.Value
			if !slices.Contains(guidelines.Names(), name.Value) {
				problems = append(problems, at(name.Line, entry+" is not a guideline; ignored"))
				continue
			}
			var b bool
			if on.Tag != "!!bool" || on.Decode(&b) != nil {
				problems = append(problems, wrong(name.Line, entry, "is not true or false"))
				continue
			}
			c.Guidelines[name.Value] = b
		}
		return problems
	},
}

// checkKeys decodes a group of Checks' keys, those of the Checks `group`, into a Config.
func checkKeys(group []string) func(c *Config, key, value *yaml.Node) []string {
	return func(c *Config, key, value *yaml.Node) []string {
		if value.Tag == "!!null" {
			return nil
		}
		if value.Kind != yaml.MappingNode {
			return []string{wrong(key.Line, key.Value, "is not a map of checks to true or false")}
		}
		if c.Checks == nil {
			c.Checks = map[string]bool{}
		}
		var problems []string
		for i := 0; i+1 < len(value.Content); i += 2 {
			name, on := value.Content[i], value.Content[i+1]
			entry := key.Value + "." + name.Value
			if !slices.Contains(group, name.Value) {
				problems = append(problems, at(name.Line, entry+" is not a check; ignored"))
				continue
			}
			if settings, ok := checkSettings[name.Value]; ok && on.Kind == yaml.MappingNode {
				c.Checks[name.Value] = true
				problems = append(problems, settings(c, entry, on)...)
				continue
			}
			var b bool
			if on.Tag != "!!bool" || on.Decode(&b) != nil {
				problems = append(problems, wrong(name.Line, entry, "is not true or false"))
				continue
			}
			c.Checks[name.Value] = b
		}
		return problems
	}
}

// checkSettings decode the settings a Check takes instead of true, the map `value` at `entry`, into
// a Config, which turns it on, and return what is wrong with them; each wrong one keeps its
// default.
var checkSettings = map[string]func(c *Config, entry string, value *yaml.Node) []string{
	"conventional-commits": func(c *Config, entry string, value *yaml.Node) []string {
		return commitRules(&c.CommitRules, entry, value)
	},
	"no-large-files": func(c *Config, entry string, value *yaml.Node) []string {
		var problems []string
		for i := 0; i+1 < len(value.Content); i += 2 {
			key, v := value.Content[i], value.Content[i+1]
			setting := entry + "." + key.Value
			if key.Value != "max-size" {
				problems = append(problems, at(key.Line, setting+" is not a setting of no-large-files; ignored"))
				continue
			}
			var n int
			if v.Tag != "!!int" || v.Decode(&n) != nil || n < 1 {
				problems = append(problems, wrong(key.Line, setting, "is not a size of 1 KB or more"))
				continue
			}
			c.MaxFileKB = n
		}
		return problems
	},
}

// commitRules decodes conventional-commits' settings, the map `value` at `entry`, into `rules`, and
// returns what is wrong with them; each wrong one keeps its default.
func commitRules(rules *checks.CommitRules, entry string, value *yaml.Node) []string {
	var problems []string
	for i := 0; i+1 < len(value.Content); i += 2 {
		key, v := value.Content[i], value.Content[i+1]
		setting := entry + "." + key.Value
		switch key.Value {
		case "types":
			var types []string
			switch {
			case v.Tag == "!!str" && v.Value == "any":
				rules.AnyType = true
			case v.Kind == yaml.SequenceNode && v.Decode(&types) == nil:
				rules.Types = types
			default:
				problems = append(problems, wrong(key.Line, setting, "is not a list of types or any"))
			}
		case "max-length":
			var n int
			if v.Tag != "!!int" || v.Decode(&n) != nil || n < 0 {
				problems = append(problems, wrong(key.Line, setting, "is not a length of 0 or more"))
				continue
			}
			rules.MaxLength = &n
		default:
			why := " is not a setting of conventional-commits; ignored"
			problems = append(problems, at(key.Line, setting+why))
		}
	}
	return problems
}

// statusLayout decodes the Status line's settings, the map `value` at `entry`, and returns what is
// wrong with them; each wrong one keeps its default, a wrong bar in the list is left out.
func statusLayout(entry string, value *yaml.Node) (statusline.Layout, []string) {
	layout := statusline.Default()
	bars := strings.Join(statusline.Bars, ", ")
	var problems []string
	for i := 0; i+1 < len(value.Content); i += 2 {
		key, v := value.Content[i], value.Content[i+1]
		setting := entry + "." + key.Value
		switch key.Value {
		case "bars":
			var names []string
			if v.Kind != yaml.SequenceNode || v.Decode(&names) != nil {
				problems = append(problems, wrong(key.Line, setting, "is not a list of "+bars))
				continue
			}
			layout.Bars = []string{}
			for j, name := range names {
				switch {
				case !slices.Contains(statusline.Bars, name):
					why := ": " + name + " is not one of " + bars + "; ignored"
					problems = append(problems, at(v.Content[j].Line, setting+why))
				case slices.Contains(layout.Bars, name):
					problems = append(problems, at(v.Content[j].Line, setting+": "+name+" is there twice; ignored"))
				default:
					layout.Bars = append(layout.Bars, name)
				}
			}
		case "thresholds":
			if v.Kind != yaml.MappingNode {
				problems = append(problems, wrong(key.Line, setting, "is not a map of bars to thresholds"))
				continue
			}
			for j := 0; j+1 < len(v.Content); j += 2 {
				name, t := v.Content[j], v.Content[j+1]
				bar := setting + "." + name.Value
				got, ok := layout.Thresholds[name.Value]
				if !ok {
					problems = append(problems, at(name.Line, bar+" is not one of "+bars+"; ignored"))
					continue
				}
				if why := thresholds(&got, t); why != "" {
					problems = append(problems, wrong(name.Line, bar, why))
					continue
				}
				if !statusline.Ordered(name.Value, got) {
					problems = append(problems, wrong(name.Line, bar, "turns red before yellow"))
					continue
				}
				layout.Thresholds[name.Value] = got
			}
		default:
			problems = append(problems, at(key.Line, setting+" is not a setting of status-line; ignored"))
		}
	}
	return layout, problems
}

// thresholds decodes a bar's thresholds, the map `value`, into `t`, and says what is wrong with
// them, or "".
func thresholds(t *statusline.Thresholds, value *yaml.Node) string {
	const why = "is not { yellow: <percent>, red: <percent> }"
	if value.Kind != yaml.MappingNode {
		return why
	}
	for i := 0; i+1 < len(value.Content); i += 2 {
		var n int
		if v := value.Content[i+1]; v.Tag != "!!int" || v.Decode(&n) != nil || n < 0 || n > 100 {
			return why
		}
		switch value.Content[i].Value {
		case "yellow":
			t.Yellow = n
		case "red":
			t.Red = n
		default:
			return why
		}
	}
	return ""
}

// at is the problem `text` at line `line` of the Config.
func at(line int, text string) string {
	return fmt.Sprintf("%s line %d: %s", names.Config, line, text)
}

// wrong is the problem of the setting `name` at line `line`, whose value is wrong as `why` says,
// so its default applies.
func wrong(line int, name, why string) string {
	return at(line, name+": "+why+"; its default applies")
}

// newConfig is a new Config, with the Guidelines `fit` on: it names the schema for editors, and
// says in plain words how the settings work, for someone who has read neither the schema nor the
// README. The keys of each section are sorted, so one is found by its name.
func newConfig(fit []string) string {
	var list, hookList, gitHookList strings.Builder
	for _, name := range slices.Sorted(slices.Values(guidelines.Names())) {
		fmt.Fprintf(&list, "  %s: %t\n", name, slices.Contains(fit, name))
	}
	for _, name := range slices.Sorted(slices.Values(checks.HookChecks)) {
		fmt.Fprintf(&hookList, "  %s: true\n", name)
	}
	for _, name := range slices.Sorted(slices.Values(checks.GitHookChecks)) {
		fmt.Fprintf(&gitHookList, "  %s: true\n", name)
	}
	return "# yaml-language-server: $schema=" + names.Schema + `
#
# baloo's settings for this repo. Each Check and each Guideline turns on or off with a key of its
# own here. A wrong setting is reported at session start, and its default applies.

# The Output style for Claude's replies, picked at session start in the settings file that
# enables the plugin (the project's .claude/settings.local.json for the user's settings), where no
# settings file of Claude Code's picks one; false picks none.
output-style: short-replies

# The plugin's Status line, set at session start in .claude/settings.local.json, where no
# settings file of Claude Code's but the user's own sets one; false takes it out. Instead of
# true it also takes its bars, in the order shown, and the percentages at which each turns yellow
# and red, such as { bars: [context, 5h], thresholds: { context: { yellow: 30, red: 50 } } };
# cache's are of the cache's lifetime left, so red is below yellow.
status-line: true

# The Session review: when a session ends, a separate Claude session records in .about/glossary.md,
# .about/adr/ and .about/inbox.md what the conversation settled or left open but nobody wrote
# down; the next session start says what it changed. It never commits.
session-review: true

# The Stop check: when Claude ends a turn that changed the working tree, it runs this command in
# the repo's root and hands a failure back to Claude to fix before it stops. Off without it, or
# with false.
# stop-check: mise run check

# Format on edit: after each of Claude's edits to a file in the repo, it runs this command in the
# repo's root with the file's path at the end, and says nothing of how it went. Off without it, or
# with false.
# format-on-edit: npx prettier --write

# Guidelines, the plugin's working rules, which Claude reads when a task calls for one; each
# one on is named to Claude at session start. A stack's is on where the repo had that stack
# when this file was made, ci where it had a CI's config, and dependencies where it had a package
# manager's manifest.
guidelines:
` + list.String() + `
# Checks, each on with true and off with false.
#
# Checks in Claude Code's hooks deny, or ask you about, a tool call of Claude's that would destroy
# work, bypass the Git hooks or show a secret. They are on without their key too.
claude-hooks:
` + hookList.String() + `
# Checks in Git hooks check every commit or push, yours or Claude's. The Git hooks are written
# where at least one of their Checks is on. conventional-commits also takes its settings instead
# of true, such as { types: [feat, fix], max-length: 72 }; types: any takes any type,
# max-length: 0 any length. no-large-files takes { max-size: 5000 }, in KB; 1024 without it.
git-hooks:
` + gitHookList.String()
}

// command decodes a setting that names a command, into the field `field` gives, or turns it off
// with false.
func command(field func(c *Config) *string) func(c *Config, key, value *yaml.Node) []string {
	return func(c *Config, key, value *yaml.Node) []string {
		var off bool
		if value.Tag == "!!bool" && value.Decode(&off) == nil && !off {
			return nil
		}
		if value.Tag != "!!str" || strings.TrimSpace(value.Value) == "" {
			return []string{wrong(key.Line, key.Value, "is not a command or false")}
		}
		*field(c) = value.Value
		return nil
	}
}

// repo is the root of the repo `dir` is in, where its Config is: the nearest folder up from `dir`
// that holds a .git, or `dir` itself outside a repo, with whether `dir` is in a repo at all.
func repo(dir string) (string, bool) {
	for d := dir; ; {
		if _, err := os.Stat(filepath.Join(d, ".git")); err == nil {
			return d, true
		}
		parent := filepath.Dir(d)
		if parent == d {
			return dir, false
		}
		d = parent
	}
}

// Load reads the Config of the repo `dir` is in, with its problems, after creating it when the
// repo has none (see create); it also returns the path of one it created. Outside a repo, when the
// repo is the home folder itself (a dotfiles repo), or when it is in Claude Code's own folder, it
// neither reads nor writes one, and every setting has its default: the home folder's .claude/ is
// Claude Code's own settings, not a repo's, and what is inside it is Claude Code's to write.
func Load(dir string) (c Config, created string, problems []string) {
	root, inRepo := repo(dir)
	if !inRepo || claudeCodes(root) {
		return c, "", nil
	}
	created, err := create(root)
	var pathErr *fs.PathError
	switch {
	case errors.As(err, &pathErr): // it names the path already
		problems = append(problems, fmt.Sprintf("could not create %s: %v", pathErr.Path, pathErr.Err))
	case err != nil:
		problems = append(problems, fmt.Sprintf("could not create %s: %v", names.Config, err))
	}
	c, more := read(root)
	c.Root = root
	return c, created, append(problems, more...)
}

// Read reads the Config of the repo `dir` is in, as Load does, but never creates one, and leaves
// its problems for session start to report.
func Read(dir string) Config {
	root, inRepo := repo(dir)
	if !inRepo || claudeCodes(root) {
		return Config{}
	}
	c, _ := read(root)
	c.Root = root
	return c
}

// Inspect reads the Config of the repo `dir` is in, as Read does, with its problems, and returns
// its path, or "" where the repo has none or no Config is read.
func Inspect(dir string) (c Config, path string, problems []string) {
	root, inRepo := repo(dir)
	if !inRepo || claudeCodes(root) {
		return Config{}, "", nil
	}
	c, problems = read(root)
	c.Root = root
	if _, err := os.Stat(filepath.Join(root, names.Config)); err == nil {
		path = filepath.Join(root, names.Config)
	}
	return c, path, problems
}

func read(root string) (Config, []string) {
	data, err := os.ReadFile(filepath.Join(root, names.Config))
	if errors.Is(err, fs.ErrNotExist) {
		return Config{}, nil
	}
	if err != nil {
		return Config{}, []string{fmt.Sprintf("%s: %v; none of it applies", names.Config, err)}
	}
	return parse(data)
}

func parse(data []byte) (Config, []string) {
	var c Config
	var doc yaml.Node
	if err := yaml.Unmarshal(data, &doc); err != nil {
		why := strings.TrimPrefix(err.Error(), "yaml: ")
		return c, []string{fmt.Sprintf("%s: %s; none of it applies", names.Config, why)}
	}
	if len(doc.Content) == 0 { // empty, or only comments
		return c, nil
	}
	top := doc.Content[0]
	if top.Kind != yaml.MappingNode {
		return c, []string{fmt.Sprintf("%s line %d: not a map of settings; none of it applies",
			names.Config, top.Line)}
	}
	var problems []string
	for i := 0; i+1 < len(top.Content); i += 2 {
		key, value := top.Content[i], top.Content[i+1]
		set, ok := keys[key.Value]
		if !ok {
			problems = append(problems, at(key.Line, key.Value+" is not a setting; ignored"))
			continue
		}
		problems = append(problems, set(&c, key, value)...)
	}
	return c, problems
}

// create writes a new Config, every Check on and the Guidelines that fit the repo, at the repo root
// `root` when it has none, and returns its path; with a Config there already, it writes nothing and
// returns "". The repo is looked through for its stacks before the file is made, so it never sits
// empty for longer than one write.
func create(root string) (string, error) {
	path := filepath.Join(root, names.Config)
	if _, err := os.Lstat(path); err == nil {
		return "", nil
	}
	text := newConfig(guidelines.Fitting(root))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return "", err
	}
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if errors.Is(err, fs.ErrExist) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	_, err = f.WriteString(text)
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		// Half a Config would pass for the user's own from then on, and never be written again.
		os.Remove(path)
		return "", err
	}
	return path, nil
}

// claudeCodes says whether the repo root `root` is the home folder, or Claude Code's own folder,
// CLAUDE_CONFIG_DIR or ~/.claude, or inside it, such as a marketplace it cloned.
func claudeCodes(root string) bool {
	home, err := os.UserHomeDir()
	if err == nil && resolve(root) == resolve(home) {
		return true
	}
	own := settings.Own()
	if own == "" {
		return false
	}
	rel, err := filepath.Rel(resolve(own), resolve(root))
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

// resolve is the path `p` with its links followed, so two spellings of one folder compare equal.
func resolve(p string) string {
	if r, err := filepath.EvalSymlinks(p); err == nil {
		return r
	}
	return filepath.Clean(p)
}
