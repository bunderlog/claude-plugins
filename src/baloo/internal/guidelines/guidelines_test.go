package guidelines

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

// write writes each file of `files`, by its path from `root`, with its text.
func write(t *testing.T, root string, files map[string]string) {
	t.Helper()
	for path, text := range files {
		path = filepath.Join(root, path)
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}

func TestFitting(t *testing.T) {
	always := []string{"principles", "design", "testing", "debugging", "writing-for-agents"}
	for _, tc := range []struct {
		name  string
		files map[string]string
		want  []string
	}{
		{"no stack", map[string]string{"README.md": "go.mod vue"}, always},
		{"go.mod at any depth", map[string]string{"src/app/go.mod": "module app\n"},
			append(always, "dependencies", "go")},
		{"a package.json naming typescript and vue", map[string]string{
			"web/package.json": `{"devDependencies": {"typescript": "^5"}, "dependencies": {"vue": "^3"}}`,
		}, append(always, "dependencies", "typescript", "vue")},
		{"a package.json naming tailwindcss", map[string]string{
			"web/package.json": `{"devDependencies": {"tailwindcss": "^4"}}`,
		}, append(always, "dependencies", "tailwind")},
		{"a package.json naming neither", map[string]string{
			"package.json": `{"name": "vue", "scripts": {"typescript": "tsc"}}`,
		}, append(always, "dependencies")},
		{"not JSON", map[string]string{"package.json": `{"dependencies": {"vue": `},
			append(always, "dependencies")},
		{"a Cargo.toml", map[string]string{"crates/x/Cargo.toml": "[package]\n"},
			append(always, "dependencies")},
		{"a pyproject.toml", map[string]string{"pyproject.toml": "[project]\n"},
			append(always, "dependencies")},
		{"a GitHub Actions workflow", map[string]string{".github/workflows/ci.yml": "on: push\n"},
			append(always, "ci")},
		{"a Jenkinsfile", map[string]string{"Jenkinsfile": "pipeline {}\n"}, append(always, "ci")},
		{"a .github with no workflows", map[string]string{".github/CODEOWNERS": "* @a\n"}, always},
		{"a CI's config below the root", map[string]string{"tools/.gitlab-ci.yml": "test: {}\n"},
			always},
		{"another project's code", map[string]string{
			"node_modules/x/package.json": `{"dependencies": {"vue": "^3"}}`,
			"vendor/x/go.mod":             "module x\n",
			".cache/go.mod":               "module x\n",
			"tools/testdata/go.mod":       "module x\n",
			"target/web/package.json":     `{"dependencies": {"vue": "^3"}}`,
			"dist/Cargo.toml":             "[package]\n",
		}, always},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			write(t, root, tc.files)
			if got := Fitting(root); !slices.Equal(got, tc.want) {
				t.Errorf("Fitting = %q; want %q", got, tc.want)
			}
		})
	}
}

// In zsh, session start adds the rules zsh needs after the rules for every task.
func TestIndex_Zsh(t *testing.T) {
	plugin := t.TempDir()
	write(t, plugin, map[string]string{"guidelines/principles.md": "# P\n\n" + everyTask + "\n\n- one\n\n" +
		inZsh + "\n\n- quote globs\n\n## Next\n"})
	on := map[string]bool{"principles": true}
	for shell, want := range map[string]bool{"zsh": true, "bash": false, "": false} {
		text, err := Index(plugin, on, shell)
		if got := strings.Contains(text, "- one\nIn zsh:\n- quote globs\n"); got != want || err != nil {
			t.Errorf("Index in %q = %q, %v; want the zsh rules %v", shell, text, err, want)
		}
	}
	if text, _ := Index(plugin, map[string]bool{"go": true}, "zsh"); strings.Contains(text, "zsh") {
		t.Errorf("Index without principles = %q; want no zsh rules", text)
	}
}

// when is the When of the Guideline `name`.
func when(name string) string {
	return All[slices.IndexFunc(All, func(g Guideline) bool { return g.Name == name })].When
}

func TestIndex(t *testing.T) {
	plugin := t.TempDir()
	if text, err := Index(plugin, map[string]bool{"go": false}, ""); text != "" || err != nil {
		t.Errorf("Index with none on = %q, %v; want nothing", text, err)
	}
	// Without the rules for every task, the lines are still there; a Guideline given by the file
	// Claude works on has none.
	lines := "Read a file when its task comes up:\n" +
		"- " + when("principles") + ": " + filepath.Join(plugin, "guidelines", "principles.md") + "\n" +
		"- " + when("go") + ": " + filepath.Join(plugin, "guidelines", "go.md")
	on := map[string]bool{"principles": true, "go": true, "vue": true, "typescript": true, "testing": true}
	if text, err := Index(plugin, on, ""); err == nil || !strings.HasSuffix(text, lines) {
		t.Errorf("Index without principles.md = %q, %v; want the lines and an error", text, err)
	}
	write(t, plugin, map[string]string{"guidelines/principles.md": "# P\n\n## Other\n\nx\n"})
	if text, err := Index(plugin, on, ""); err == nil || !strings.HasSuffix(text, lines) ||
		strings.Contains(text, "On every task") {
		t.Errorf("Index of a principles.md without %q = %q, %v; want the lines and an error", everyTask, text, err)
	}
	head := "Guidelines, the plugin's working rules; the project's own CLAUDE.md, config and linters " +
		"win where they conflict.\nOn every task:\n"
	for _, tc := range []struct{ name, file, rules string }{
		{"LF", "# P\n\n" + everyTask + "\n\n- one\n- two\n\n## Next\n\nlater\n", "- one\n- two\n"},
		{"CRLF", "# P\r\n\r\n" + everyTask + "\r\n\r\n- one\r\n- two\r\n\r\n## Next\r\n", "- one\n- two\n"},
		{"a space after the heading, a deeper one inside", "# P\n\n" + everyTask + " \n- one\n### Sub\n- two\n",
			"- one\n### Sub\n- two\n"},
		{"the heading first", everyTask + "\n- one\n", "- one\n"},
	} {
		write(t, plugin, map[string]string{"guidelines/principles.md": tc.file})
		if got, err := Index(plugin, on, ""); got != head+tc.rules+lines || err != nil {
			t.Errorf("Index, %s = %q, %v; want %q", tc.name, got, err, head+tc.rules+lines)
		}
	}
}

// A Guideline given by the file Claude works on comes whole, once a session, where the Config
// turns it on, and each one given is logged.
func TestForFile(t *testing.T) {
	plugin, data := t.TempDir(), t.TempDir()
	write(t, plugin, map[string]string{"guidelines/typescript.md": "# TypeScript\n\nNo any.\n",
		"guidelines/vue.md": "# Vue\n\nScript setup.\n", "guidelines/testing.md": "# Testing\n\nRed first.\n"})
	on := map[string]bool{"typescript": true, "vue": true, "testing": true}
	for rel, want := range map[string][]string{
		"src/a.ts": {"typescript"}, "src/App.vue": {"typescript", "vue"}, "x/a_test.go": {"testing"},
		"src/a.test.ts": {"typescript", "testing"}, "tests/test_a.py": {"testing"}, "src/__tests__/a.js": {"testing"},
		"src/a.go": nil, "README.md": nil, "src/testing.ts": {"typescript"},
	} {
		text, err := ForFile(plugin, t.TempDir(), "", rel, on)
		var got []string
		for _, name := range []string{"typescript", "vue", "testing"} {
			if strings.Contains(text, "The "+name+" Guideline applies to "+rel) {
				got = append(got, name)
			}
		}
		if err != nil || !slices.Equal(got, want) {
			t.Errorf("ForFile(%s) gave %q, %v; want %q", rel, got, err, want)
		}
	}
	text, err := ForFile(plugin, data, "s1", "src/App.vue", on)
	if err != nil || !strings.Contains(text, "# Vue\n\nScript setup.") || !strings.Contains(text, "# TypeScript\n\nNo any.") {
		t.Errorf("ForFile = %q, %v; want both Guidelines whole", text, err)
	}
	if again, _ := ForFile(plugin, data, "s1", "src/b.ts", on); again != "" {
		t.Errorf("ForFile again in the session = %q; want nothing", again)
	}
	if other, _ := ForFile(plugin, data, "s2", "src/b.ts", map[string]bool{"vue": true}); other != "" {
		t.Errorf("ForFile of a Guideline turned off = %q; want nothing", other)
	}
	log, _ := os.ReadFile(filepath.Join(data, "guidelines", "guidelines.log"))
	lines := strings.Split(strings.TrimSpace(string(log)), "\n")
	if len(lines) != 2 || !strings.HasSuffix(lines[0], "\ts1\ttypescript\tsrc/App.vue") ||
		!strings.HasSuffix(lines[1], "\ts1\tvue\tsrc/App.vue") {
		t.Errorf("log = %q; want a line per Guideline given: when, session, Guideline, file", log)
	}
}
