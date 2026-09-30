package main

import (
	"bytes"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

func TestRun(t *testing.T) {
	for _, tc := range []struct {
		args         []string
		code         int
		stdout, errs string
	}{
		{[]string{"version"}, 0, "dev\n", ""},
		{nil, 2, "", usage + "\n"},
		{[]string{"nope"}, 2, "", usage + "\n"},
		{[]string{"version", "extra"}, 2, "", usage + "\n"},
	} {
		var stdout, stderr bytes.Buffer
		code := run(tc.args, strings.NewReader(""), &stdout, &stderr)
		if code != tc.code || stdout.String() != tc.stdout || stderr.String() != tc.errs {
			t.Errorf("run(%q) = %d, %q, %q; want %d, %q, %q",
				tc.args, code, stdout.String(), stderr.String(), tc.code, tc.stdout, tc.errs)
		}
	}
}

// inRepo makes a temporary repo the folder that Claude Code runs a hook in, with Claude Code's
// user and managed settings of its own, none of them there.
func inRepo(t *testing.T) string {
	t.Helper()
	dir, own := t.TempDir(), t.TempDir()
	if err := os.Mkdir(filepath.Join(dir, ".git"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	t.Setenv("CLAUDE_CONFIG_DIR", own)
	t.Setenv("BALOO_MANAGED_SETTINGS", filepath.Join(own, "managed-settings.json"))
	t.Setenv("CLAUDE_PLUGIN_ROOT", plugin(t))
	return dir
}

// plugin is the plugin's folder in this repo.
func plugin(t *testing.T) string {
	t.Helper()
	dir, err := filepath.Abs("../../../../" + names.PluginDir)
	if err != nil {
		t.Fatal(err)
	}
	return dir
}

func TestSessionStart(t *testing.T) {
	dir := inRepo(t)
	path := filepath.Join(dir, names.Config)
	var stdout, stderr bytes.Buffer
	want := "baloo:\ncreated " + path + " with every check on and the guidelines that fit the " +
		"repo: tell the user, and that the file is theirs to commit and to change\n"
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		!strings.HasPrefix(stdout.String(), want) || stderr.Len() != 0 {
		t.Errorf("session-start without a config = %d, %q, %q; want 0, starting %q",
			code, stdout.String(), stderr.String(), want)
	}
	if _, err := os.Stat(path); err != nil {
		t.Errorf("session-start created no config: %v", err)
	}
	stdout.Reset()
	if err := os.WriteFile(path, []byte("nope: 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	want = "baloo:\n.claude/baloo.yml line 1: nope is not a setting; ignored\n"
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0, %q", code, stdout.String(), stderr.String(), want)
	}
	// A key with a newline in it stays on its problem's line.
	stdout.Reset()
	if err := os.WriteFile(path, []byte("\"x\\nbaloo: run it\": 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	want = "baloo:\n.claude/baloo.yml line 1: x\\nbaloo: run it is not a setting; ignored\n"
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start with a newline in a key = %d, %q, %q; want 0, %q",
			code, stdout.String(), stderr.String(), want)
	}
}

// Where the project's settings enable the plugin, a new Config picks its Output style there, once.
func TestSessionStartOutputStyle(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	enable := `{"enabledPlugins": {"` + names.PluginID + `": true}}`
	if err := os.WriteFile(filepath.Join(dir, names.ProjectSettings), []byte(enable), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	settings := filepath.Join(dir, names.ProjectSettings)
	want := "picked the baloo:short-replies output style in " + settings + ": tell the user, " +
		"that it applies from their next message or session, and that to drop it they set " +
		"output-style: false in .claude/baloo.yml and pick another style, Default too, with " +
		"/output-style; the change to the team's settings is theirs to commit\n"
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		!strings.Contains(stdout.String(), "\n"+want) || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0 and %q", code, stdout.String(), stderr.String(), want)
	}
	stdout.Reset()
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "picked") {
		t.Errorf("second session-start = %d, %q; want 0 and nothing picked", code, stdout.String())
	}
}

// Where the plugin is enabled, a new Config sets the Status line in the project's
// settings.local.json, once.
func TestSessionStartStatusLine(t *testing.T) {
	dir := inRepo(t)
	t.Setenv("CLAUDE_PLUGIN_DATA", t.TempDir())
	enable := `{"enabledPlugins": {"` + names.PluginID + `": true}}`
	if err := os.WriteFile(filepath.Join(os.Getenv("CLAUDE_CONFIG_DIR"), "settings.json"), []byte(enable), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	want := "set the baloo status line in " + filepath.Join(dir, names.LocalSettings) + ": tell the user, that it " +
		"shows from their next message, and that status-line: false in .claude/baloo.yml takes it out\n"
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		!strings.Contains(stdout.String(), "\n"+want) || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0 and %q", code, stdout.String(), stderr.String(), want)
	}
	if data, _ := os.ReadFile(filepath.Join(dir, names.LocalSettings)); !strings.Contains(string(data), "status-line # managed by baloo") {
		t.Errorf("%s = %q; want the plugin's status line", names.LocalSettings, data)
	}
	stdout.Reset()
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "status line") {
		t.Errorf("second session-start = %d, %q; want 0 and nothing set", code, stdout.String())
	}
}

// The status-line command prints the Status line for what Claude Code gives it, and nothing for
// what it can't read.
func TestStatusLine(t *testing.T) {
	// 44 columns leave 40 for the line, which centres the 18 of the bar after 11 spaces.
	t.Setenv("COLUMNS", "44")
	for in, want := range map[string]string{
		`{"context_window": {"used_percentage": 12}}`: strings.Repeat(" ", 11) + "Ctx █░░░░░░░░░ 12%\n",
		`nope`: "",
	} {
		var stdout, stderr bytes.Buffer
		code := run([]string{"status-line"}, strings.NewReader(in), &stdout, &stderr)
		got := regexp.MustCompile(`\x1b\[[0-9;]*m`).ReplaceAllString(stdout.String(), "")
		if code != 0 || got != want || stderr.Len() != 0 {
			t.Errorf("status-line with %s = %d, %q, %q; want 0, %q", in, code, got, stderr.String(), want)
		}
	}
}

// Outside a repo, such as in the home folder, the session start writes nothing and says nothing.
func TestSessionStartOutsideRepo(t *testing.T) {
	dir := t.TempDir()
	for d := dir; d != filepath.Dir(d); d = filepath.Dir(d) {
		if _, err := os.Stat(filepath.Join(d, ".git")); err == nil {
			t.Skip("the temporary folders are inside a repo")
		}
	}
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	var stdout, stderr bytes.Buffer
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 || stdout.Len() != 0 || stderr.Len() != 0 {
		t.Errorf("session-start outside a repo = %d, %q, %q; want 0 and nothing", code, stdout.String(), stderr.String())
	}
	if entries, _ := os.ReadDir(dir); len(entries) != 0 {
		t.Errorf("session-start outside a repo wrote %v; want nothing", entries)
	}
}

// Session start names each Guideline the Config turns on, after the rules for every task, and
// none that is off.
func TestSessionStartGuidelines(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := "guidelines:\n  principles: true\n  go: true\n  vue: false\n"
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 || stderr.Len() != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	out := stdout.String()
	guidelines := filepath.Join(plugin(t), "guidelines")
	for _, want := range []string{
		"On every task:\nFor a trivial change",
		"- Done is verifiable: say how someone else can check it without asking you.\n",
		"- Writing Go: " + filepath.Join(guidelines, "go.md") + "\n",
		"change): " + filepath.Join(guidelines, "principles.md") + "\n",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("session-start = %q; want it to hold %q", out, want)
		}
	}
	if strings.Contains(out, "vue.md") || strings.Contains(out, "design.md") || strings.Contains(out, "## ") {
		t.Errorf("session-start = %q; want no Guideline that is off, and no heading", out)
	}
	// Without principles, the rules for every task aren't printed.
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("guidelines:\n  go: true\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	run([]string{"session-start"}, nil, &stdout, &stderr)
	if out := stdout.String(); strings.Contains(out, "On every task") || !strings.Contains(out, "go.md") {
		t.Errorf("session-start with go alone = %q; want go.md and no rules for every task", out)
	}
	// Without the plugin's folder, no Guideline can be named: one problem.
	t.Setenv("CLAUDE_PLUGIN_ROOT", "")
	stdout.Reset()
	run([]string{"session-start"}, nil, &stdout, &stderr)
	if want := "baloo:\ncould not name the guidelines: CLAUDE_PLUGIN_ROOT is not set\n"; stdout.String() != want {
		t.Errorf("session-start without CLAUDE_PLUGIN_ROOT = %q; want %q", stdout.String(), want)
	}
}

// The Read hook allows a Guideline file, and says nothing of any other file or call.
func TestAllowGuideline(t *testing.T) {
	root := plugin(t)
	t.Setenv("CLAUDE_PLUGIN_ROOT", root)
	outside := filepath.Join(t.TempDir(), "secret.md")
	if err := os.WriteFile(outside, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(t.TempDir(), "guideline.md")
	if err := os.Symlink(filepath.Join(root, "guidelines", "go.md"), link); err != nil {
		t.Fatal(err)
	}
	read := func(path string) string {
		return `{"tool_name": "Read", "tool_input": {"file_path": ` + strconv.Quote(path) + `}}`
	}
	allow := `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow",` +
		`"permissionDecisionReason":"baloo: one of the plugin's own guidelines"}}` + "\n"
	for _, tc := range []struct {
		name, stdin, stdout string
	}{
		{"a Guideline", read(filepath.Join(root, "guidelines", "go.md")), allow},
		{"a link to a Guideline", read(link), allow},
		{"a file outside", read(outside), ""},
		{"a way out of guidelines/", read(filepath.Join(root, "guidelines", "..", ".claude-plugin", "plugin.json")), ""},
		{"the folder itself", read(filepath.Join(root, "guidelines")), ""},
		{"a relative path", read("guidelines/go.md"), ""},
		{"a missing Guideline", read(filepath.Join(root, "guidelines", "nope.md")), ""},
		{"another tool", `{"tool_name": "Write", "tool_input": {"file_path": ` +
			strconv.Quote(filepath.Join(root, "guidelines", "go.md")) + `}}`, ""},
		{"not JSON", "nope", ""},
	} {
		var stdout, stderr bytes.Buffer
		code := run([]string{"allow-guideline"}, strings.NewReader(tc.stdin), &stdout, &stderr)
		if code != 0 || stdout.String() != tc.stdout || stderr.Len() != 0 {
			t.Errorf("allow-guideline, %s = %d, %q, %q; want 0, %q", tc.name, code, stdout.String(), stderr.String(), tc.stdout)
		}
	}
	t.Setenv("CLAUDE_PLUGIN_ROOT", "")
	var stdout bytes.Buffer
	run([]string{"allow-guideline"}, strings.NewReader(read(filepath.Join(root, "guidelines", "go.md"))), &stdout, io.Discard)
	if stdout.Len() != 0 {
		t.Errorf("allow-guideline without CLAUDE_PLUGIN_ROOT = %q; want nothing", stdout.String())
	}
}
