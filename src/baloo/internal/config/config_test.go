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

	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
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
		{"status-line: {}\n", "unset", 1},
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
		if want := ".claude/baloo.yml line 1: status-line: is not true or false; the Status line is left as it is"; tc.problems == 1 && problems[0] != want {
			t.Errorf("parse(%q) problem = %q; want %q", tc.yml, problems[0], want)
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
	want := map[string]bool{"principles": true, "design": true, "testing": true, "writing-for-agents": true, "go": true,
		"typescript": false, "vue": false}
	if !maps.Equal(c.Guidelines, want) || problems != nil {
		t.Errorf("new config's guidelines = %v, %q; want %v", c.Guidelines, problems, want)
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
