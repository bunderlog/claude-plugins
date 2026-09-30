package settings

import (
	"os"
	"path/filepath"
	"testing"
)

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func contents(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		t.Fatal(err)
	}
	return string(data)
}

func TestSet(t *testing.T) {
	const field = `"outputStyle": "x"`
	fresh := "{\n  " + field + "\n}\n"
	for _, tc := range []struct{ data, want string }{
		{"", fresh},
		{" \n", fresh},
		{"{}", fresh},
		{"{ }", fresh},
		{"{\n}\n", fresh},
		{"{\n  \"a\": 1\n}\n", "{\n  " + field + ",\n  \"a\": 1\n}\n"},
		// A field that is there is set in place.
		{"{\n  \"a\": 1,\n  \"outputStyle\": {\"b\": [2]}\n}\n", "{\n  \"a\": 1,\n  " + field + "\n}\n"},
		{"{\"outputStyle\":null,\"a\":1}", "{\"outputStyle\":\"x\",\"a\":1}"},
		// Only a top-level field counts.
		{"{\"a\": {\"outputStyle\": 1}}", "{\n  " + field + ",\"a\": {\"outputStyle\": 1}}"},
	} {
		got, err := set([]byte(tc.data), "outputStyle", []byte(`"x"`))
		if err != nil || string(got) != tc.want {
			t.Errorf("set(%q) = %q, %v; want %q", tc.data, got, err, tc.want)
		}
	}
	for _, data := range []string{"[]", "{nope", "1", "{\"a\": 1} {"} {
		if got, err := set([]byte(data), "outputStyle", []byte(`"x"`)); err == nil {
			t.Errorf("set(%q) = %q; want an error", data, got)
		}
	}
}

// A field is taken out with its comma, and the rest of the file stays as it was.
func TestDelete(t *testing.T) {
	for _, tc := range []struct{ data, want string }{
		{"{\n  \"s\": {\"c\": 1},\n  \"a\": 1\n}\n", "{\n  \"a\": 1\n}\n"},
		{"{\n  \"a\": 1,\n  \"s\": {\"c\": 1}\n}\n", "{\n  \"a\": 1\n}\n"},
		{"{\n  \"a\": 1,\n  \"s\": 2,\n  \"b\": 3\n}\n", "{\n  \"a\": 1,\n  \"b\": 3\n}\n"},
		{"{\"s\":2,\"a\":1}", "{\"a\":1}"},
		{"{\n  \"s\": 2\n}\n", "{\n}\n"},
		{"{\n  \"a\": {\"s\": 1}\n}\n", "{\n  \"a\": {\"s\": 1}\n}\n"},
	} {
		path := filepath.Join(t.TempDir(), "settings.json")
		write(t, path, tc.data)
		if err := Delete(path, "s"); err != nil {
			t.Fatalf("Delete in %q: %v", tc.data, err)
		}
		if got := contents(t, path); got != tc.want {
			t.Errorf("Delete in %q = %q; want %q", tc.data, got, tc.want)
		}
	}
}

// A settings file is replaced whole, through a link to it too, and keeps its mode.
func TestReplace(t *testing.T) {
	dir := t.TempDir()
	real := filepath.Join(dir, "real.json")
	write(t, real, "{}")
	if err := os.Chmod(real, 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(dir, "link.json")
	if err := os.Symlink(real, link); err != nil {
		t.Fatal(err)
	}
	if err := replace(link, []byte("{\"a\": 1}")); err != nil {
		t.Fatal(err)
	}
	if got := contents(t, real); got != `{"a": 1}` {
		t.Errorf("%s = %q; want the new text", real, got)
	}
	if info, err := os.Lstat(link); err != nil || info.Mode()&os.ModeSymlink == 0 {
		t.Errorf("%s is no longer a link: %v", link, err)
	}
	if info, _ := os.Stat(real); info.Mode().Perm() != 0o600 {
		t.Errorf("%s has mode %v; want 0600 kept", real, info.Mode().Perm())
	}
	if entries, _ := os.ReadDir(dir); len(entries) != 2 {
		t.Errorf("replace left %d files in %s; want 2", len(entries), dir)
	}
}

func TestPattern(t *testing.T) {
	for rel, want := range map[string]string{
		"a/.claude/settings.local.json": "a/.claude/settings.local.json",
		"a[1]/b*/c?/d\\e":               "a\\[1]/b\\*/c\\?/d\\\\e",
		"a /x":                          "a /x",
		"#a/!b":                         "#a/!b",
		"trailing  ":                    "trailing\\ \\ ",
	} {
		if got := pattern(rel); got != want {
			t.Errorf("pattern(%q) = %q; want %q", rel, got, want)
		}
	}
}
