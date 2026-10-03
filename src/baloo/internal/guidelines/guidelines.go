// Package guidelines knows the plugin's Guidelines, the files in its guidelines/ (ADR
// guidelines): which fit a repo, what session start tells Claude of the ones the Config turns on,
// and which file the Read tool may read without asking.
package guidelines

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// A Guideline is the file `Name`.md in the plugin's guidelines/.
type Guideline struct {
	Name string
	// When is the task that calls for reading it, as its index line names it.
	When string
	// fits says whether a repo's files call for the Guideline: they name its stack, or configure
	// a CI; nil for a Guideline that fits any project.
	fits func(manifests) bool
}

// All are the plugin's Guidelines, in the order session start names them. Each is a key under
// guidelines in the Config and its schema.
var All = []Guideline{
	{"principles", "Before non-trivial work (a feature, a refactor, an architecture, API or " +
		"data-model change)", nil},
	{"design", "Designing a module or an interface, or deciding where it is tested from", nil},
	{"testing", "Writing tests, or building test-first", nil},
	{"debugging", "Finding or fixing the cause of a bug (wrong output, a crash, a failing or " +
		"flaky test, a slowdown)", nil},
	{"writing-for-agents", "Writing or editing a skill, a CLAUDE.md or AGENTS.md, or a prompt",
		nil},
	{"ci", "Fixing a failed CI run, or finding why a run, a pipeline or a PR went red",
		func(m manifests) bool { return m.ci }},
	{"go", "Writing Go", func(m manifests) bool { return m.goMod }},
	{"typescript", "Writing TypeScript",
		func(m manifests) bool { return m.packages["typescript"] }},
	{"vue", "Writing or testing a Vue component, a composable or a Pinia store, or starting a " +
		"Vue app", func(m manifests) bool { return m.packages["vue"] }},
	{"tailwind", "Styling with Tailwind CSS: classes, theme tokens, dark mode",
		func(m manifests) bool { return m.packages["tailwindcss"] }},
}

// Names are the names of All, in its order.
func Names() []string {
	names := make([]string, len(All))
	for i, g := range All {
		names[i] = g.Name
	}
	return names
}

// manifests is what a repo's files say of its stacks and its CI: whether it has a go.mod, the
// packages its package.json files depend on, and whether its root holds a CI's config.
type manifests struct {
	goMod    bool
	packages map[string]bool
	ci       bool
}

// ciConfigs are the files and folders at a repo's root that configure a CI.
var ciConfigs = []string{
	".github/workflows", ".gitlab-ci.yml", "bitbucket-pipelines.yml", "bamboo-specs",
	"Jenkinsfile", "azure-pipelines.yml", ".circleci", ".buildkite",
}

// skipped are folders the stacks aren't looked for in: another project's code, test fixtures, and
// what a build makes, which can hold more files than the repo's own code.
var skipped = map[string]bool{
	"node_modules": true, "vendor": true, "testdata": true,
	"build": true, "dist": true, "out": true, "target": true,
}

// Fitting are the names of the Guidelines that fit the repo at `root`: every one for any project,
// a stack's where a manifest at any depth names it, outside hidden folders and the skipped ones,
// and ci where the root holds a CI's config.
func Fitting(root string) []string {
	m := manifests{packages: map[string]bool{}}
	for _, name := range ciConfigs {
		if _, err := os.Stat(filepath.Join(root, name)); err == nil {
			m.ci = true
		}
	}
	filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if path != root && (strings.HasPrefix(d.Name(), ".") || skipped[d.Name()]) {
				return filepath.SkipDir
			}
			return nil
		}
		switch d.Name() {
		case "go.mod":
			m.goMod = true
		case "package.json":
			for _, name := range dependencies(path) {
				m.packages[name] = true
			}
		}
		return nil
	})
	var fit []string
	for _, g := range All {
		if g.fits == nil || g.fits(m) {
			fit = append(fit, g.Name)
		}
	}
	return fit
}

// dependencies are the packages the package.json at `path` depends on, of any kind; one that
// can't be read names none.
func dependencies(path string) []string {
	var p struct {
		Dependencies, DevDependencies, PeerDependencies, OptionalDependencies map[string]any
	}
	data, err := os.ReadFile(path)
	if err != nil || json.Unmarshal(data, &p) != nil {
		return nil
	}
	var names []string
	for _, deps := range []map[string]any{
		p.Dependencies, p.DevDependencies, p.PeerDependencies, p.OptionalDependencies,
	} {
		for name := range deps {
			names = append(names, name)
		}
	}
	return names
}

// everyTask is the heading of the section of principles.md that session start prints whole: the
// rules that must hold on every task.
const everyTask = "## On every task"

// inZsh is the heading of the section of principles.md that session start prints after it where
// the Bash tool's shell is zsh: the rules zsh needs.
const inZsh = "## In zsh"

// Index is what session start tells Claude of the Guidelines `on` in the plugin at `plugin`: a
// line for each, when to read it and its path, after the rules for every task when principles is
// on, and the rules zsh needs where `shell`, the Bash tool's, is zsh. With none on it is "". When
// the rules can't be read, it is the lines without them, and why.
func Index(plugin string, on map[string]bool, shell string) (string, error) {
	var lines []string
	for _, g := range All {
		if on[g.Name] {
			lines = append(lines, fmt.Sprintf("- %s: %s", g.When, path(plugin, g.Name)))
		}
	}
	if len(lines) == 0 {
		return "", nil
	}
	text := "Guidelines, the plugin's working rules; the project's own CLAUDE.md, config and " +
		"linters win where they conflict.\n"
	var err error
	if on["principles"] {
		var rules string
		if rules, err = section(path(plugin, "principles"), everyTask); err == nil {
			text += "On every task:\n" + rules + "\n"
		}
		if rules, zshErr := section(path(plugin, "principles"), inZsh); shell == "zsh" && err == nil {
			if err = zshErr; err == nil {
				text += "In zsh:\n" + rules + "\n"
			}
		}
	}
	return text + "Read a file when its task comes up:\n" + strings.Join(lines, "\n"), err
}

func path(plugin, name string) string {
	return filepath.Join(plugin, "guidelines", name+".md")
}

// section is the text under the line `heading` in the Markdown file at `file`, up to the next
// heading of its level, whatever its line endings and the spaces around the heading.
func section(file, heading string) (string, error) {
	data, err := os.ReadFile(file)
	if err != nil {
		return "", err
	}
	level := heading[:strings.IndexByte(heading, ' ')+1]
	var body []string
	in := false
	for _, line := range strings.Split(strings.ReplaceAll(string(data), "\r\n", "\n"), "\n") {
		switch {
		case strings.TrimSpace(line) == heading:
			in = true
		case in && strings.HasPrefix(line, level):
			return strings.TrimSpace(strings.Join(body, "\n")), nil
		case in:
			body = append(body, strings.TrimRight(line, " \t"))
		}
	}
	if !in {
		return "", fmt.Errorf("%s has no %q", file, heading)
	}
	return strings.TrimSpace(strings.Join(body, "\n")), nil
}

// Readable says whether `file` is a Guideline file of the plugin at `plugin`, a file right in
// its guidelines/, once links are followed; a path that isn't absolute is none.
func Readable(plugin, file string) bool {
	if plugin == "" || !filepath.IsAbs(file) {
		return false
	}
	dir, err := filepath.EvalSymlinks(filepath.Join(plugin, "guidelines"))
	if err != nil {
		return false
	}
	real, err := filepath.EvalSymlinks(file)
	if err != nil {
		return false
	}
	info, err := os.Stat(real)
	if err != nil || !info.Mode().IsRegular() {
		return false
	}
	return filepath.Dir(real) == dir
}
