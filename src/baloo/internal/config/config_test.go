package config

import (
	"encoding/json"
	"errors"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"testing"

	"go.yaml.in/yaml/v3"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/statusline"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// tempRepo is a temporary git repo, as far as repo can tell, with a folder inside it.
func tempRepo(t *testing.T) (root, sub string) {
	t.Helper()
	root = t.TempDir()
	sub = filepath.Join(root, "a", "b")
	if err := os.MkdirAll(filepath.Join(root, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(sub, 0o755); err != nil {
		t.Fatal(err)
	}
	return root, sub
}

// outsideRepo is a temporary folder in no repo. When the temporary folders are inside one
// themselves, a test that needs it is skipped: every walk up would reach that repo.
func outsideRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if _, ok := repo(dir); ok {
		t.Skip("the temporary folders are inside a repo")
	}
	return dir
}

// writeConfig writes a Config of `text` at `root`.
func writeConfig(t *testing.T, root, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Join(root, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, names.Config), []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestRepo(t *testing.T) {
	root, sub := tempRepo(t)
	if got, ok := repo(sub); got != root || !ok {
		t.Errorf("repo(%s) = %s, %v; want the repo's root %s", sub, got, ok, root)
	}
	// A worktree or a submodule has a .git file, not a folder.
	inner := filepath.Join(sub, "worktree")
	if err := os.MkdirAll(inner, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(inner, ".git"), []byte("gitdir: elsewhere\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if got, ok := repo(inner); got != inner || !ok {
		t.Errorf("repo(%s) = %s, %v; want the worktree itself", inner, got, ok)
	}
	t.Run("outside a repo", func(t *testing.T) {
		outside := outsideRepo(t)
		if got, ok := repo(outside); got != outside || ok {
			t.Errorf("repo(%s) = %s, %v; want the folder itself, not a repo", outside, got, ok)
		}
	})
}

func TestParse(t *testing.T) {
	for _, tc := range []struct {
		name, yml string
		problems  []string
	}{
		{"a new config", newConfig(guidelines.Names()), nil},
		{"an empty file", "", nil},
		{"only comments", "# nothing yet\n", nil},
		{"an empty map", "{}\n", nil},
		{"keys that aren't settings", "# a comment\nnope: true\nalso: [1]\n", []string{
			".claude/baloo.yml line 2: nope is not a setting; ignored",
			".claude/baloo.yml line 3: also is not a setting; ignored",
		}},
		{"a list", "- a\n- b\n", []string{
			".claude/baloo.yml line 1: not a map of settings; none of it applies",
		}},
		{"a scalar", "true\n", []string{
			".claude/baloo.yml line 1: not a map of settings; none of it applies",
		}},
		{"not YAML", "a: [1\n", []string{
			".claude/baloo.yml: line 1: did not find expected ',' or ']'; none of it applies",
		}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if _, problems := parse([]byte(tc.yml)); !slices.Equal(problems, tc.problems) {
				t.Errorf("problems = %q; want %q", problems, tc.problems)
			}
		})
	}
}

// A setting whose value doesn't decode is a problem, and the settings around it still apply.
func TestParseSetting(t *testing.T) {
	var got []string
	keys["probe"] = func(c *Config, key, value *yaml.Node) []string {
		var b bool
		if err := value.Decode(&b); err != nil {
			return []string{wrong(key.Line, key.Value, "is not true or false")}
		}
		got = append(got, value.Value)
		return nil
	}
	t.Cleanup(func() { delete(keys, "probe") })
	_, problems := parse([]byte("probe: true\nnope: 1\nprobe: maybe\n"))
	want := []string{
		".claude/baloo.yml line 2: nope is not a setting; ignored",
		".claude/baloo.yml line 3: probe: is not true or false; its default applies",
	}
	if !slices.Equal(problems, want) || !slices.Equal(got, []string{"true"}) {
		t.Errorf("problems = %q, set %q; want %q, set [true]", problems, got, want)
	}
}

// Load reads the Config at the repo's root from any folder inside it, and a Config it can't read,
// or can't create, is one problem.
func TestLoadProblems(t *testing.T) {
	root, sub := tempRepo(t)
	if err := os.MkdirAll(filepath.Join(root, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, names.Config)
	if err := os.WriteFile(path, []byte("nope: 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, problems := Load(sub); len(problems) != 1 || !strings.Contains(problems[0], "nope is not a setting") {
		t.Errorf("Load from a folder inside the repo = %q; want the root config's problem", problems)
	}
	if os.Getuid() == 0 {
		t.Skip("root reads and writes whatever the permissions say")
	}
	if err := os.Chmod(path, 0o000); err != nil {
		t.Fatal(err)
	}
	if _, _, problems := Load(sub); len(problems) != 1 || !strings.HasSuffix(problems[0], "none of it applies") {
		t.Errorf("Load of an unreadable config = %q; want one problem", problems)
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(filepath.Join(root, ".claude"), 0o555); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.Chmod(filepath.Join(root, ".claude"), 0o755) })
	want := "could not create " + path + ": permission denied"
	if _, created, problems := Load(sub); created != "" || !slices.Equal(problems, []string{want}) {
		t.Errorf("Load where .claude/ is read-only = %q, %q; want %q", created, problems, want)
	}
}

func TestLoad(t *testing.T) {
	root, sub := tempRepo(t)
	_, created, problems := Load(sub)
	if want := filepath.Join(root, names.Config); created != want || problems != nil {
		t.Fatalf("Load without a config = %s, %q; want %s created", created, problems, want)
	}
	if data, err := os.ReadFile(created); err != nil || string(data) != newConfig(guidelines.Fitting(root)) {
		t.Errorf("new config = %q, %v; want the template", data, err)
	}
	path := created
	if err := os.WriteFile(path, []byte("nope: 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, created, problems := Load(root); created != "" || len(problems) != 1 {
		t.Errorf("Load with a config = %q, %q; want nothing created and its one problem", created, problems)
	}
	if data, _ := os.ReadFile(path); string(data) != "nope: 1\n" {
		t.Errorf("Load changed a config that was there to %q", data)
	}
	// The home folder as a repo, a dotfiles one, with a folder in it that isn't a repo of its own.
	home, inHome := tempRepo(t)
	t.Setenv("HOME", home)
	if _, created, problems := Load(inHome); created != "" || problems != nil {
		t.Errorf("Load in the home folder's repo = %q, %q; want nothing created", created, problems)
	}
	if _, err := os.Stat(filepath.Join(home, ".claude")); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("Load in the home folder's repo made %s/.claude: %v", home, err)
	}
	// Its .claude/ is Claude Code's own, so a baloo.yml there is not read either.
	writeConfig(t, home, "nope: 1\n")
	if _, _, problems := Load(inHome); problems != nil {
		t.Errorf("Load in the home folder's repo read %s: %q", names.Config, problems)
	}
	// The same, reached through a link to the home folder.
	link := filepath.Join(t.TempDir(), "home")
	if err := os.Symlink(home, link); err != nil {
		t.Fatal(err)
	}
	t.Setenv("HOME", link)
	if _, created, problems := Load(inHome); created != "" || problems != nil {
		t.Errorf("Load in the home folder's repo, HOME a link to it = %q, %q; want nothing created", created, problems)
	}
	// Claude Code's own folder as a repo, and a repo inside it, such as a marketplace it cloned.
	t.Setenv("CLAUDE_CONFIG_DIR", "")
	own := filepath.Join(home, ".claude")
	for _, root := range []string{own, filepath.Join(own, "plugins", "marketplaces", "m")} {
		if err := os.MkdirAll(filepath.Join(root, ".git"), 0o755); err != nil {
			t.Fatal(err)
		}
		if _, created, _ := Load(root); created != "" {
			t.Errorf("Load in %s created %s; want nothing created", root, created)
		}
	}
	// The same folder moved by CLAUDE_CONFIG_DIR, while ~/.claude is no longer Claude Code's.
	moved, inMoved := tempRepo(t)
	t.Setenv("CLAUDE_CONFIG_DIR", moved)
	if _, created, _ := Load(inMoved); created != "" {
		t.Errorf("Load in CLAUDE_CONFIG_DIR created %s; want nothing created", created)
	}
	if _, created, _ := Load(own); created == "" {
		t.Errorf("Load in ~/.claude with CLAUDE_CONFIG_DIR elsewhere created nothing; want a Config")
	}
	t.Run("outside a repo", func(t *testing.T) {
		outside := outsideRepo(t)
		if _, created, problems := Load(outside); created != "" || problems != nil {
			t.Errorf("Load outside a repo = %q, %q; want nothing created", created, problems)
		}
		if entries, _ := os.ReadDir(outside); len(entries) != 0 {
			t.Errorf("Load outside a repo wrote %v; want nothing", entries)
		}
		writeConfig(t, outside, "nope: 1\n")
		if _, _, problems := Load(outside); problems != nil {
			t.Errorf("Load outside a repo read %s: %q", names.Config, problems)
		}
	})
}

// The schema editors check a config against lists the settings keys has, and no others.
func TestSchema(t *testing.T) {
	data, err := os.ReadFile("../../../../" + names.PluginDir + "/schema.json")
	if err != nil {
		t.Fatal(err)
	}
	var schema struct {
		Properties           map[string]json.RawMessage
		AdditionalProperties *bool
	}
	if err := json.Unmarshal(data, &schema); err != nil {
		t.Fatal(err)
	}
	got := slices.Sorted(maps.Keys(schema.Properties))
	want := slices.Sorted(maps.Keys(keys))
	if !slices.Equal(got, want) || schema.AdditionalProperties == nil || *schema.AdditionalProperties {
		t.Errorf("schema has %q, additionalProperties %v; want %q and false", got, schema.AdditionalProperties, want)
	}
	if !strings.HasSuffix(names.Schema, "/"+names.PluginDir+"/schema.json") {
		t.Errorf("names.Schema = %s; want the URL of %s/schema.json", names.Schema, names.PluginDir)
	}
}

// Every Output style the Config can name is a file in the plugin's output-styles/, and the schema
// names the same.
func TestOutputStyles(t *testing.T) {
	entries, err := os.ReadDir("../../../../" + names.PluginDir + "/output-styles")
	if err != nil {
		t.Fatal(err)
	}
	var files []string
	for _, e := range entries {
		if name, ok := strings.CutSuffix(e.Name(), ".md"); ok && e.Type().IsRegular() {
			files = append(files, name)
		}
	}
	if !slices.Equal(files, slices.Sorted(slices.Values(OutputStyles))) {
		t.Errorf("output-styles/ has %q; want %q", files, OutputStyles)
	}
	data, err := os.ReadFile("../../../../" + names.PluginDir + "/schema.json")
	if err != nil {
		t.Fatal(err)
	}
	var schema struct {
		Properties map[string]struct{ Enum []any }
	}
	if err := json.Unmarshal(data, &schema); err != nil {
		t.Fatal(err)
	}
	var enum []string
	for _, v := range schema.Properties["output-style"].Enum {
		if s, ok := v.(string); ok {
			enum = append(enum, s)
		}
	}
	if !slices.Equal(enum, OutputStyles) {
		t.Errorf("schema's output-style names %q; want %q", enum, OutputStyles)
	}
}

func TestOutputStyleSetting(t *testing.T) {
	for _, tc := range []struct {
		yml, style string
		problems   int
	}{
		{"output-style: short-replies\n", "short-replies", 0},
		{"output-style: false\n", "", 0},
		{"output-style: true\n", "", 1},
		{"output-style: nope\n", "", 1},
		{"output-style: [short-replies]\n", "", 1},
		{"# none\n", "", 0},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.OutputStyle != tc.style || len(problems) != tc.problems {
			t.Errorf("parse(%q) = %q, %q; want %q and %d problems", tc.yml, c.OutputStyle, problems, tc.style, tc.problems)
		}
	}
}

func TestStatusLineSetting(t *testing.T) {
	for _, tc := range []struct {
		yml      string
		on       string
		problems int
	}{
		{"status-line: true\n", "true", 0},
		{"status-line: false\n", "false", 0},
		{"status-line: yes please\n", "unset", 1},
		{"status-line: [context]\n", "unset", 1},
		{"status-line: {}\n", "true", 0},
		{"# none\n", "unset", 0},
	} {
		c, problems := parse([]byte(tc.yml))
		got := "unset"
		if c.StatusLine != nil {
			got = strconv.FormatBool(*c.StatusLine)
		}
		if got != tc.on || len(problems) != tc.problems {
			t.Errorf("parse(%q) = %s, %q; want %s and %d problems", tc.yml, got, problems, tc.on, tc.problems)
		}
		if want := ".claude/baloo.yml line 1: status-line: is not true, false or its bars and thresholds; the Status line is left as it is"; tc.problems == 1 && problems[0] != want {
			t.Errorf("parse(%q) problem = %q; want %q", tc.yml, problems[0], want)
		}
	}
}

// The Status line takes its bars, in order, and their thresholds; a wrong one is a problem, and
// its default applies, a wrong bar in the list left out. Without them the default Layout applies.
func TestStatusLayoutSetting(t *testing.T) {
	def := statusline.Default()
	for _, tc := range []struct {
		yml        string
		bars       []string
		thresholds map[string]statusline.Thresholds
		problems   []string
	}{
		{"status-line: {}\n", def.Bars, def.Thresholds, nil},
		{"status-line:\n  bars: [7d, context]\n  thresholds:\n    context: {red: 50}\n    cache: {yellow: 50, red: 10}\n",
			[]string{"7d", "context"}, map[string]statusline.Thresholds{
				"context": {Yellow: 15, Red: 50}, "cache": {Yellow: 50, Red: 10},
				"5h": {Yellow: 70, Red: 85}, "7d": {Yellow: 80, Red: 95},
			}, nil},
		{"status-line:\n  bars: []\n", []string{}, def.Thresholds, nil},
		{"status-line:\n  bars:\n    - context\n    - ctx\n    - context\n  thresholds:\n    context: {yellow: 30, red: 20}\n" +
			"    cache: {yellow: 10, red: 20}\n    5h: {yellow: 101}\n    7d: {blue: 1}\n    week: {red: 1}\n  colors: true\n",
			[]string{"context"}, def.Thresholds, []string{
				".claude/baloo.yml line 4: status-line.bars: ctx is not one of context, cache, 5h, 7d; ignored",
				".claude/baloo.yml line 5: status-line.bars: context is there twice; ignored",
				".claude/baloo.yml line 7: status-line.thresholds.context: turns red before yellow; its default applies",
				".claude/baloo.yml line 8: status-line.thresholds.cache: turns red before yellow; its default applies",
				".claude/baloo.yml line 9: status-line.thresholds.5h: is not { yellow: <percent>, red: <percent> }; its default applies",
				".claude/baloo.yml line 10: status-line.thresholds.7d: is not { yellow: <percent>, red: <percent> }; its default applies",
				".claude/baloo.yml line 11: status-line.thresholds.week is not one of context, cache, 5h, 7d; ignored",
				".claude/baloo.yml line 12: status-line.colors is not a setting of status-line; ignored",
			}},
		{"status-line:\n  bars: context\n  thresholds: [1]\n", def.Bars, def.Thresholds, []string{
			".claude/baloo.yml line 2: status-line.bars: is not a list of context, cache, 5h, 7d; its default applies",
			".claude/baloo.yml line 3: status-line.thresholds: is not a map of bars to thresholds; its default applies",
		}},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.StatusLine == nil || !*c.StatusLine || c.StatusLayout == nil {
			t.Errorf("parse(%q) = %v, %v; want the Status line on with a Layout", tc.yml, c.StatusLine, c.StatusLayout)
			continue
		}
		if l := c.StatusLayout; !slices.Equal(l.Bars, tc.bars) || !maps.Equal(l.Thresholds, tc.thresholds) || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %v, %v, %q; want %v, %v, %q", tc.yml, l.Bars, l.Thresholds, problems, tc.bars, tc.thresholds, tc.problems)
		}
	}
	if c, _ := parse([]byte("status-line: true\n")); c.StatusLayout != nil {
		t.Errorf("status-line: true = %v; want no Layout, for the default", c.StatusLayout)
	}
}

// The Session review is on with its key, off without it, and on in a new Config (ADR
// session-review).
func TestSessionReviewSetting(t *testing.T) {
	for _, tc := range []struct {
		yml      string
		on       bool
		problems []string
	}{
		{"session-review: true\n", true, nil},
		{"session-review: false\n", false, nil},
		{"# none\n", false, nil},
		{"session-review: yes please\n", false, []string{
			".claude/baloo.yml line 1: session-review: is not true or false; its default applies"}},
		{newConfig(nil), true, nil},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.SessionReview != tc.on || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %t, %q; want %t, %q", tc.yml, c.SessionReview, problems, tc.on, tc.problems)
		}
	}
}

// Each Guideline turns on with its own key under guidelines, and a wrong entry is a problem at its
// own line while the entries beside it apply.
func TestGuidelinesSetting(t *testing.T) {
	for _, tc := range []struct {
		yml      string
		on       []string
		problems []string
	}{
		{"guidelines:\n  principles: true\n  go: true\n  vue: false\n", []string{"go", "principles"}, nil},
		{"guidelines:\n", nil, nil},
		{"guidelines:\n  nope: true\n  go: yes please\n  design: true\n", []string{"design"}, []string{
			".claude/baloo.yml line 2: guidelines.nope is not a guideline; ignored",
			".claude/baloo.yml line 3: guidelines.go: is not true or false; its default applies",
		}},
		{"guidelines: true\n", nil, []string{
			".claude/baloo.yml line 1: guidelines: is not a map of guidelines to true or false; its default applies",
		}},
	} {
		c, problems := parse([]byte(tc.yml))
		var on []string
		for name, ok := range c.Guidelines {
			if ok {
				on = append(on, name)
			}
		}
		slices.Sort(on)
		if !slices.Equal(on, tc.on) || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %q, %q; want %q, %q", tc.yml, on, problems, tc.on, tc.problems)
		}
	}
}

// A new Config turns on the Guidelines for any project, and a stack's only where the repo has it.
func TestNewConfigGuidelines(t *testing.T) {
	root, sub := tempRepo(t)
	if err := os.WriteFile(filepath.Join(sub, "go.mod"), []byte("module x\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	c, _, problems := Load(root)
	want := map[string]bool{"principles": true, "design": true, "testing": true, "debugging": true,
		"writing-for-agents": true, "ci": false, "dependencies": true, "go": true,
		"typescript": false, "vue": false, "tailwind": false}
	if !maps.Equal(c.Guidelines, want) || problems != nil {
		t.Errorf("new config's guidelines = %v, %q; want %v", c.Guidelines, problems, want)
	}
}

// A new Config's guidelines, claude-hooks and git-hooks list their keys sorted.
func TestNewConfigSorted(t *testing.T) {
	var doc yaml.Node
	if err := yaml.Unmarshal([]byte(newConfig(nil)), &doc); err != nil {
		t.Fatal(err)
	}
	top := doc.Content[0].Content
	for i := 0; i < len(top); i += 2 {
		var keys []string
		for j := 0; j < len(top[i+1].Content); j += 2 {
			keys = append(keys, top[i+1].Content[j].Value)
		}
		if top[i+1].Kind == yaml.MappingNode && !slices.IsSorted(keys) {
			t.Errorf("new config's %s = %q; want them sorted", top[i].Value, keys)
		}
	}
}

// Every Guideline is a file in the plugin's guidelines/, and the schema has a key for each.
func TestGuidelines(t *testing.T) {
	entries, err := os.ReadDir("../../../../" + names.PluginDir + "/guidelines")
	if err != nil {
		t.Fatal(err)
	}
	var files []string
	for _, e := range entries {
		if name, ok := strings.CutSuffix(e.Name(), ".md"); ok && e.Type().IsRegular() {
			files = append(files, name)
		}
	}
	want := slices.Sorted(slices.Values(guidelines.Names()))
	if !slices.Equal(files, want) {
		t.Errorf("guidelines/ has %q; want %q", files, want)
	}
	data, err := os.ReadFile("../../../../" + names.PluginDir + "/schema.json")
	if err != nil {
		t.Fatal(err)
	}
	var schema struct {
		Properties map[string]struct {
			Properties           map[string]json.RawMessage
			AdditionalProperties *bool
		}
	}
	if err := json.Unmarshal(data, &schema); err != nil {
		t.Fatal(err)
	}
	g := schema.Properties["guidelines"]
	if got := slices.Sorted(maps.Keys(g.Properties)); !slices.Equal(got, want) ||
		g.AdditionalProperties == nil || *g.AdditionalProperties {
		t.Errorf("schema's guidelines has %q, additionalProperties %v; want %q and false", got, g.AdditionalProperties, want)
	}
}

// stop-check names the command the Stop check runs; without it, or false, it is off, and a new
// Config has it only as a comment (ADR stop-check).
func TestStopCheckSetting(t *testing.T) {
	for _, tc := range []struct {
		yml, command string
		problems     []string
	}{
		{"stop-check: mise run check\n", "mise run check", nil},
		{"stop-check: false\n", "", nil},
		{"# none\n", "", nil},
		{"stop-check: \"\"\n", "", []string{
			".claude/baloo.yml line 1: stop-check: is not a command or false; its default applies"}},
		{"stop-check: [make, test]\n", "", []string{
			".claude/baloo.yml line 1: stop-check: is not a command or false; its default applies"}},
		{newConfig(nil), "", nil},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.StopCheck != tc.command || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %q, %q; want %q, %q", tc.yml, c.StopCheck, problems, tc.command, tc.problems)
		}
	}
	if !strings.Contains(newConfig(nil), "\n# stop-check: mise run check\n") {
		t.Error("a new Config has no stop-check example")
	}
}

// format-on-edit names the command run on each file Claude edits; without it, or false, it is off,
// and a new Config has it only as a comment (ADR format-on-edit).
func TestFormatOnEditSetting(t *testing.T) {
	for _, tc := range []struct {
		yml, command string
		problems     []string
	}{
		{"format-on-edit: npx prettier --write\n", "npx prettier --write", nil},
		{"format-on-edit: false\n", "", nil},
		{"format-on-edit: [prettier]\n", "", []string{
			".claude/baloo.yml line 1: format-on-edit: is not a command or false; its default applies"}},
		{newConfig(nil), "", nil},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.FormatOnEdit != tc.command || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %q, %q; want %q, %q", tc.yml, c.FormatOnEdit, problems, tc.command, tc.problems)
		}
	}
	if !strings.Contains(newConfig(nil), "\n# format-on-edit: npx prettier --write\n") {
		t.Error("a new Config has no format-on-edit example")
	}
}

// Each Check turns on or off with its own key under the group that runs it, and a wrong entry is a
// problem at its own line while the entries beside it apply. Without its key, a Check a Hook runs
// is on and a Git hook's is off (ADR checks).
func TestChecksSetting(t *testing.T) {
	all := append(slices.Clone(checks.GitHookChecks), checks.HookChecks...)
	for _, tc := range []struct {
		yml      string
		on       []string
		problems []string
	}{
		{"git-hooks:\n  no-ai-coauthor: true\nclaude-hooks:\n  no-secrets-in-context: false\n",
			[]string{"no-ai-coauthor", "no-destructive-commands", "no-git-hook-bypass"}, nil},
		{"", checks.HookChecks, nil},
		{"claude-hooks:\ngit-hooks:\n", checks.HookChecks, nil},
		{"git-hooks:\n  nope: true\n  linear-history: yes please\n  no-secrets-in-context: false\n" +
			"claude-hooks:\n  no-destructive-commands: false\n  no-ai-coauthor: true\n",
			[]string{"no-git-hook-bypass", "no-secrets-in-context"}, []string{
				".claude/baloo.yml line 2: git-hooks.nope is not a check; ignored",
				".claude/baloo.yml line 3: git-hooks.linear-history: is not true or false; its default applies",
				".claude/baloo.yml line 4: git-hooks.no-secrets-in-context is not a check; ignored",
				".claude/baloo.yml line 7: claude-hooks.no-ai-coauthor is not a check; ignored",
			}},
		{"git-hooks: true\n", checks.HookChecks, []string{
			".claude/baloo.yml line 1: git-hooks: is not a map of checks to true or false; its default applies",
		}},
		{"checks:\n  no-ai-coauthor: true\n", checks.HookChecks, []string{
			".claude/baloo.yml line 1: checks is not a setting; ignored",
		}},
		{"git-hooks:\n  conventional-commits:\n    types: any\n", []string{"conventional-commits",
			"no-destructive-commands", "no-git-hook-bypass", "no-secrets-in-context"}, nil},
	} {
		c, problems := parse([]byte(tc.yml))
		var on []string
		for _, name := range all {
			if c.CheckOn(name) {
				on = append(on, name)
			}
		}
		slices.Sort(on)
		want := slices.Sorted(slices.Values(tc.on))
		if !slices.Equal(on, want) || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %q, %q; want %q, %q", tc.yml, on, problems, want, tc.problems)
		}
	}
}

// conventional-commits takes its types, a list or any, and its longest line, 0 for none; a wrong
// setting is a problem, and its default applies.
func TestConventionalCommitsSetting(t *testing.T) {
	max72, none := 72, 0
	for _, tc := range []struct {
		yml      string
		rules    checks.CommitRules
		problems []string
	}{
		{"git-hooks:\n  conventional-commits: true\n", checks.CommitRules{}, nil},
		{"git-hooks:\n  conventional-commits:\n    types: [feat, fix]\n    max-length: 72\n",
			checks.CommitRules{Types: []string{"feat", "fix"}, MaxLength: &max72}, nil},
		{"git-hooks:\n  conventional-commits:\n    types: any\n    max-length: 0\n",
			checks.CommitRules{AnyType: true, MaxLength: &none}, nil},
		{"git-hooks:\n  conventional-commits:\n    types: some\n    max-length: -1\n    nope: 1\n",
			checks.CommitRules{}, []string{
				".claude/baloo.yml line 3: git-hooks.conventional-commits.types: is not a list of types or any; its default applies",
				".claude/baloo.yml line 4: git-hooks.conventional-commits.max-length: is not a length of 0 or more; its default applies",
				".claude/baloo.yml line 5: git-hooks.conventional-commits.nope is not a setting of conventional-commits; ignored",
			}},
	} {
		c, problems := parse([]byte(tc.yml))
		got := c.CommitRules
		if !slices.Equal(got.Types, tc.rules.Types) || got.AnyType != tc.rules.AnyType ||
			(got.MaxLength == nil) != (tc.rules.MaxLength == nil) ||
			got.MaxLength != nil && *got.MaxLength != *tc.rules.MaxLength ||
			!c.CheckOn("conventional-commits") || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %+v, %q; want %+v, %q", tc.yml, got, problems, tc.rules, tc.problems)
		}
	}
}

// no-large-files takes its limit, in KB, of 1 or more; a wrong setting is a problem, and its
// default applies.
func TestNoLargeFilesSetting(t *testing.T) {
	for _, tc := range []struct {
		yml      string
		maxKB    int
		problems []string
	}{
		{"git-hooks:\n  no-large-files: true\n", 0, nil},
		{"git-hooks:\n  no-large-files:\n    max-size: 5000\n", 5000, nil},
		{"git-hooks:\n  no-large-files:\n    max-size: 0\n    nope: 1\n", 0, []string{
			".claude/baloo.yml line 3: git-hooks.no-large-files.max-size: is not a size of 1 KB or more; its default applies",
			".claude/baloo.yml line 4: git-hooks.no-large-files.nope is not a setting of no-large-files; ignored",
		}},
	} {
		c, problems := parse([]byte(tc.yml))
		if c.MaxFileKB != tc.maxKB || !c.CheckOn("no-large-files") || !slices.Equal(problems, tc.problems) {
			t.Errorf("parse(%q) = %d, %v, %q; want %d, on, %q", tc.yml, c.MaxFileKB, c.CheckOn("no-large-files"),
				problems, tc.maxKB, tc.problems)
		}
	}
}

// A new Config turns every Check on, and the schema has a key for each under the group that runs
// it.
func TestChecks(t *testing.T) {
	root, _ := tempRepo(t)
	c, _, problems := Load(root)
	all := append(slices.Clone(checks.GitHookChecks), checks.HookChecks...)
	for _, name := range all {
		if on, ok := c.Checks[name]; !ok || !on {
			t.Errorf("new config's %s = %v, %v; want true", name, on, ok)
		}
	}
	if problems != nil {
		t.Errorf("new config's problems = %q", problems)
	}
	data, err := os.ReadFile("../../../../" + names.PluginDir + "/schema.json")
	if err != nil {
		t.Fatal(err)
	}
	var schema struct {
		Properties map[string]struct {
			Properties map[string]json.RawMessage
		}
	}
	if err := json.Unmarshal(data, &schema); err != nil {
		t.Fatal(err)
	}
	for group, want := range map[string][]string{"claude-hooks": checks.HookChecks,
		"git-hooks": checks.GitHookChecks} {
		got := slices.Sorted(maps.Keys(schema.Properties[group].Properties))
		if want := slices.Sorted(slices.Values(want)); !slices.Equal(got, want) {
			t.Errorf("schema's %s = %q; want %q", group, got, want)
		}
	}
}

// Read reads a Config as Load does, but never creates one.
func TestRead(t *testing.T) {
	root, sub := tempRepo(t)
	if c := Read(sub); c.Root != root || !c.CheckOn("no-secrets-in-context") {
		t.Errorf("Read without a config = %+v; want the root %s and the defaults", c, root)
	}
	if _, err := os.Stat(filepath.Join(root, names.Config)); err == nil {
		t.Error("Read created a config")
	}
	writeConfig(t, root, "claude-hooks:\n  no-secrets-in-context: false\n")
	if c := Read(sub); c.CheckOn("no-secrets-in-context") {
		t.Error("Read = no-secrets-in-context on; want the config's false")
	}
}
