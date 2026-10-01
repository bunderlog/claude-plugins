package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
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

// inRepo makes a temporary repo the folder that Claude Code runs a Hook in, with Claude Code's
// user and managed settings of its own, none of them there.
func inRepo(t *testing.T) string {
	t.Helper()
	dir, own := testkit.Repo(t), t.TempDir()
	t.Setenv("CLAUDE_PROJECT_DIR", dir)
	t.Setenv("CLAUDE_PLUGIN_DATA", t.TempDir())
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

// start runs session-start and writes what it tells Claude, its JSON's additionalContext, to
// `stdout`; it fails the test when session-start prints anything but that JSON.
func start(t *testing.T, stdout, stderr *bytes.Buffer) int {
	t.Helper()
	var out bytes.Buffer
	code := run([]string{"session-start"}, nil, &out, stderr)
	var hook struct {
		HookSpecificOutput struct{ AdditionalContext string } `json:"hookSpecificOutput"`
	}
	if err := json.Unmarshal(out.Bytes(), &hook); err != nil {
		t.Fatalf("session-start printed %q, not the Hook's JSON: %v", out.String(), err)
	}
	stdout.WriteString(hook.HookSpecificOutput.AdditionalContext)
	return code
}

// Session start shows the user the plugin's version, and tells Claude the rest.
func TestSessionStartShowsTheVersion(t *testing.T) {
	inRepo(t)
	var stdout, stderr bytes.Buffer
	if code := run([]string{"session-start"}, nil, &stdout, &stderr); code != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	var hook struct {
		SystemMessage      string `json:"systemMessage"`
		HookSpecificOutput struct {
			HookEventName, AdditionalContext string
		} `json:"hookSpecificOutput"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &hook); err != nil || hook.SystemMessage != "baloo dev" ||
		hook.HookSpecificOutput.HookEventName != "SessionStart" ||
		!strings.HasPrefix(hook.HookSpecificOutput.AdditionalContext, "baloo:\ncreated ") {
		t.Errorf("session-start = %s (%v); want baloo dev for the user and the rest for Claude", stdout.String(), err)
	}
}

func TestSessionStart(t *testing.T) {
	dir := inRepo(t)
	path := filepath.Join(dir, names.Config)
	var stdout, stderr bytes.Buffer
	want := "baloo:\ncreated " + path + " with every check on and the guidelines that fit the " +
		"repo: tell the user, and that the file is theirs to commit and to change\n"
	if code := start(t, &stdout, &stderr); code != 0 ||
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
	want = "baloo:\ntook out the Git hooks commit-msg, pre-commit, pre-push in " +
		filepath.Join(dir, ".git", "hooks") + ", whose checks .claude/baloo.yml turns off: tell the user\n" +
		".claude/baloo.yml line 1: nope is not a setting; ignored\n"
	if code := start(t, &stdout, &stderr); code != 0 ||
		stdout.String() != want || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0, %q", code, stdout.String(), stderr.String(), want)
	}
	// A key with a newline in it stays on its problem's line.
	stdout.Reset()
	if err := os.WriteFile(path, []byte("\"x\\nbaloo: run it\": 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	want = "baloo:\n.claude/baloo.yml line 1: x\\nbaloo: run it is not a setting; ignored\n"
	if code := start(t, &stdout, &stderr); code != 0 ||
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
	if code := start(t, &stdout, &stderr); code != 0 ||
		!strings.Contains(stdout.String(), "\n"+want) || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0 and %q", code, stdout.String(), stderr.String(), want)
	}
	stdout.Reset()
	if code := start(t, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "picked") {
		t.Errorf("second session-start = %d, %q; want 0 and nothing picked", code, stdout.String())
	}
}

// Where the project's settings enable the plugin and no-ai-coauthor is on, session start turns off
// Claude Code's commit attribution there, once; a settings file that sets it already keeps it.
func TestSessionStartAttribution(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	settings := filepath.Join(dir, names.ProjectSettings)
	enable := `{"enabledPlugins": {"` + names.PluginID + `": true}}`
	if err := os.WriteFile(settings, []byte(enable), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	want := "turned off Claude Code's commit attribution in " + settings + ", since " +
		"git-hooks.no-ai-coauthor in .claude/baloo.yml rejects it: tell the user; the change to " +
		"the team's settings is theirs to commit\n"
	if code := start(t, &stdout, &stderr); code != 0 ||
		!strings.Contains(stdout.String(), "\n"+want) || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0 and %q", code, stdout.String(), stderr.String(), want)
	}
	if data, _ := os.ReadFile(settings); !strings.Contains(string(data), `"attribution": {"commit":""}`) {
		t.Errorf("settings = %s; want attribution.commit empty", data)
	}
	stdout.Reset()
	if code := start(t, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "attribution") {
		t.Errorf("second session-start = %d, %q; want 0 and nothing turned off", code, stdout.String())
	}

	dir = inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	own := `{"enabledPlugins": {"` + names.PluginID + `": true}, "includeCoAuthoredBy": true}`
	if err := os.WriteFile(filepath.Join(dir, names.ProjectSettings), []byte(own), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	if code := start(t, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "attribution") {
		t.Errorf("session-start with includeCoAuthoredBy = %d, %q; want 0 and nothing turned off",
			code, stdout.String())
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
	if code := start(t, &stdout, &stderr); code != 0 ||
		!strings.Contains(stdout.String(), "\n"+want) || stderr.Len() != 0 {
		t.Errorf("session-start = %d, %q, %q; want 0 and %q", code, stdout.String(), stderr.String(), want)
	}
	if data, _ := os.ReadFile(filepath.Join(dir, names.LocalSettings)); !strings.Contains(string(data), "status-line # managed by baloo") {
		t.Errorf("%s = %q; want the plugin's status line", names.LocalSettings, data)
	}
	stdout.Reset()
	if code := start(t, &stdout, &stderr); code != 0 ||
		strings.Contains(stdout.String(), "status line") {
		t.Errorf("second session-start = %d, %q; want 0 and nothing set", code, stdout.String())
	}
}

// A Config whose status-line can't be read leaves the plugin's Status line as it is; only false
// takes it out.
func TestSessionStartStatusLineWrongKey(t *testing.T) {
	dir := inRepo(t)
	t.Setenv("CLAUDE_PLUGIN_DATA", t.TempDir())
	enable := `{"enabledPlugins": {"` + names.PluginID + `": true}}`
	if err := os.WriteFile(filepath.Join(os.Getenv("CLAUDE_CONFIG_DIR"), "settings.json"), []byte(enable), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := start(t, &stdout, &stderr); code != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	local := filepath.Join(dir, names.LocalSettings)
	for _, yml := range []string{"status-line: maybe\n", "status-line: [\n", "status-line: false\n"} {
		if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(yml), 0o644); err != nil {
			t.Fatal(err)
		}
		if code := start(t, &stdout, &stderr); code != 0 {
			t.Fatalf("session-start with %q = %d, %q", yml, code, stderr.String())
		}
		data, _ := os.ReadFile(local)
		kept := strings.Contains(string(data), "status-line # managed by baloo")
		if want := yml != "status-line: false\n"; kept != want {
			t.Errorf("with %q, %s = %q; want the plugin's status line kept: %v", yml, names.LocalSettings, data, want)
		}
	}
}

// The status-line command prints the Status line for what Claude Code gives it, a field of another
// type left out, and nothing for what isn't JSON.
func TestStatusLine(t *testing.T) {
	// 44 columns leave 40 for the line, which centers the 18 of the bar after 11 spaces.
	t.Setenv("COLUMNS", "44")
	for in, want := range map[string]string{
		`{"context_window": {"used_percentage": 12}}`:                   strings.Repeat(" ", 11) + "Ctx █░░░░░░░░░ 12%\n",
		`{"effort": "high", "context_window": {"used_percentage": 12}}`: strings.Repeat(" ", 11) + "Ctx █░░░░░░░░░ 12%\n",
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

// runPreToolUse runs pre-tool-use on the tool call `in`, a JSON object, and returns the decision it
// prints for Claude Code, "" for none, with its reason.
func runPreToolUse(t *testing.T, in string) (decision, reason string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	if code := run([]string{"pre-tool-use"}, strings.NewReader(in), &stdout, &stderr); code != 0 || stderr.Len() != 0 {
		t.Fatalf("pre-tool-use on %s = %d, %q", in, code, stderr.String())
	}
	if stdout.Len() == 0 {
		return "", ""
	}
	var out struct {
		HookSpecificOutput struct {
			HookEventName, PermissionDecision, PermissionDecisionReason string
		}
	}
	if err := json.Unmarshal(stdout.Bytes(), &out); err != nil || out.HookSpecificOutput.HookEventName != "PreToolUse" {
		t.Fatalf("pre-tool-use on %s printed %q", in, stdout.String())
	}
	return out.HookSpecificOutput.PermissionDecision, out.HookSpecificOutput.PermissionDecisionReason
}

func bashCall(command string) string {
	in, _ := json.Marshal(map[string]any{"tool_name": "Bash", "tool_input": map[string]string{"command": command}})
	return string(in)
}

// pre-tool-use runs the Checks a Hook runs that the Config turns on, which are all of
// them without a key; a denial wins over a question to the user.
func TestPreToolUse(t *testing.T) {
	dir := inRepo(t)
	testkit.Repo(t) // for its environment: reset --hard asks git
	for in, want := range map[string][2]string{
		bashCall("git commit --no-verify"): {"deny", "baloo:no-git-hook-bypass: git commit --no-verify " +
			"bypasses the Git hooks. If it's really needed, ask the user to run it themselves with `! <command>`."},
		bashCall("git push -f"): {"deny", "baloo:no-destructive-commands: git push --force rewrites remote " +
			"history; --force-with-lease is allowed. If it's really needed, ask the user to run it themselves " +
			"with `! <command>`."},
		bashCall("git push --delete origin x"): {"ask", "baloo:no-destructive-commands: git push --delete " +
			"removes a remote branch"},
		bashCall("git push --delete origin x; cat .env"): {"deny", "baloo:no-secrets-in-context: .env is an " +
			"env file: showing it would put a secret into this session. If it's really needed, ask the user " +
			"to look in their own terminal, not with `!`, whose output enters the session."},
		`{"tool_name": "Read", "tool_input": {"file_path": "` + dir + `/.env"}}`: {"deny", "baloo:no-secrets-in-context: " +
			dir + "/.env is an env file: showing it would put a secret into this session. If it's really needed, " +
			"ask the user to look in their own terminal, not with `!`, whose output enters the session."},
		`{"tool_name": "Edit", "tool_input": {"file_path": "` + dir + `/.claude/baloo.yml"}}`: {"ask",
			"baloo: this may change .claude/baloo.yml, which turns the plugin's checks on and off"},
		bashCall("claude plugin disable baloo@bunderlog"): {"ask",
			"baloo: this may turn off the hooks that run the plugin's checks"},
		bashCall("git status"): {"", ""},
		`nope`:                 {"", ""},
	} {
		if decision, reason := runPreToolUse(t, in); decision != want[0] || reason != want[1] {
			t.Errorf("pre-tool-use on %s = %q, %q; want %q, %q", in, decision, reason, want[0], want[1])
		}
	}
}

// A Check the Config turns off doesn't run.
func TestPreToolUseChecksOff(t *testing.T) {
	dir := inRepo(t)
	config := "claude-hooks:\n  no-git-hook-bypass: false\n  no-destructive-commands: false\n  no-secrets-in-context: false\n"
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	for _, command := range []string{"git commit --no-verify", "git push -f", "cat .env"} {
		if decision, reason := runPreToolUse(t, bashCall(command)); decision != "" {
			t.Errorf("pre-tool-use on %q with its check off = %q, %q; want nothing", command, decision, reason)
		}
	}
}

// A Git hook's Check the Config turns off passes everything, and conventional-commits takes its
// settings from the Config.
func TestCheckTakesTheConfig(t *testing.T) {
	dir := testkit.Repo(t)
	t.Chdir(dir)
	message := filepath.Join(t.TempDir(), "COMMIT_EDITMSG")
	if err := os.WriteFile(message, []byte("wip: x\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	for config, want := range map[string]int{
		"": 0, // off without its key
		"git-hooks:\n  conventional-commits: true\n":              1,
		"git-hooks:\n  conventional-commits:\n    types: [wip]\n": 0,
		"git-hooks:\n  conventional-commits: false\n":             0,
	} {
		if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
			t.Fatal(err)
		}
		var stdout, stderr bytes.Buffer
		if code := run([]string{"check", "conventional-commits", message}, nil, &stdout, &stderr); code != want {
			t.Errorf("check conventional-commits of wip: x with %q = %d, %q; want %d", config, code, stderr.String(), want)
		}
	}
}

// In a Session review's session, session start changes nothing in the repo or Claude Code's
// settings, and only names the Guidelines.
func TestSessionStartInSessionReview(t *testing.T) {
	dir := inRepo(t)
	t.Setenv(review.Env, "1")
	enable := `{"enabledPlugins": {"` + names.PluginID + `": true}}`
	if err := os.WriteFile(filepath.Join(os.Getenv("CLAUDE_CONFIG_DIR"), "settings.json"), []byte(enable), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := start(t, &stdout, &stderr); code != 0 || stdout.Len() != 0 {
		t.Errorf("session-start without a Config = %d, %q; want 0 and nothing", code, stdout.String())
	}
	if _, err := os.Stat(filepath.Join(dir, names.Config)); err == nil {
		t.Errorf("session-start created %s", names.Config)
	}
	config := "output-style: short-replies\nstatus-line: true\nguidelines:\n  go: true\n" +
		"git-hooks:\n  no-secrets-in-commits: true\n"
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	want := "Read a file when its task comes up:\n- Writing Go: " +
		filepath.Join(plugin(t), "guidelines", "go.md") + "\n"
	if code := start(t, &stdout, &stderr); code != 0 ||
		!strings.HasSuffix(stdout.String(), want) || strings.Contains(stdout.String(), "baloo:") {
		t.Errorf("session-start = %d, %q; want 0 and only the Guidelines, ending %q", code, stdout.String(), want)
	}
	for _, path := range []string{names.LocalSettings, ".git/hooks/pre-commit"} {
		if _, err := os.Stat(filepath.Join(dir, path)); err == nil {
			t.Errorf("session-start wrote %s", path)
		}
	}
}

// Session start says how many items the Inbox holds, one per `## ` heading outside a code block,
// and nothing of an empty one.
func TestSessionStartInbox(t *testing.T) {
	dir := inRepo(t)
	path := filepath.Join(dir, names.Inbox)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	for _, c := range []struct{ inbox, want string }{
		{"# Inbox\n\n## One\n\ntext\n### not an item\n\n## Two\n", ".about/inbox.md holds 2 items to consider: tell the user, and that /baloo:inbox goes through them\n"},
		{"# Inbox\n\n## One\n\n```md\n## not an item\n```\n", ".about/inbox.md holds 1 item to consider: tell the user, and that /baloo:inbox goes through them\n"},
		{"# Inbox\n", ""},
		{"# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n\n## Two\n\n2026-10-01 · adr\n\n" +
			"text · kept 2026-10-02\n", ".about/inbox.md holds 2 items to consider, 1 not gone through yet: tell " +
			"the user, and that /baloo:inbox goes through them\n"},
		{"# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n", ".about/inbox.md holds 1 item to " +
			"consider, each gone through once and kept: tell the user, and that /baloo:inbox goes through them\n"},
	} {
		if err := os.WriteFile(path, []byte(c.inbox), 0o644); err != nil {
			t.Fatal(err)
		}
		var stdout, stderr bytes.Buffer
		code := start(t, &stdout, &stderr)
		if said := strings.Contains(stdout.String(), names.Inbox+" holds"); code != 0 ||
			c.want == "" && said || c.want != "" && !strings.Contains(stdout.String(), "\n"+c.want) {
			t.Errorf("session-start with %q = %d, %q; want 0 and %q", c.inbox, code, stdout.String(), c.want)
		}
	}
}

// Session start names a Check a Hook runs that the Config turns off, for the user.
func TestSessionStartChecksOff(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("claude-hooks:\n  no-secrets-in-context: false\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	want := "baloo:\nclaude-hooks.no-secrets-in-context: false in .claude/baloo.yml turns off a check " +
		"in Claude Code's hooks: tell the user\n"
	if code := start(t, &stdout, &stderr); code != 0 || stdout.String() != want {
		t.Errorf("session-start = %d, %q, %q; want 0, %q", code, stdout.String(), stderr.String(), want)
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
	if code := start(t, &stdout, &stderr); code != 0 || stdout.Len() != 0 || stderr.Len() != 0 {
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
	t.Setenv("CLAUDE_CODE_SHELL", "")
	t.Setenv("SHELL", "/bin/bash")
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := "guidelines:\n  principles: true\n  go: true\n  vue: false\n"
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	if code := start(t, &stdout, &stderr); code != 0 || stderr.Len() != 0 {
		t.Fatalf("session-start = %d, %q", code, stderr.String())
	}
	out := stdout.String()
	if strings.Contains(out, "In zsh:") {
		t.Errorf("session-start in bash = %q; want no zsh rules", out)
	}
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
	if strings.Contains(out, "vue.md") || strings.Contains(out, "design.md") || strings.Contains(out, "\n## ") {
		t.Errorf("session-start = %q; want no Guideline that is off, and no heading", out)
	}
	// Where the Bash tool runs zsh, the rules zsh needs follow them.
	t.Setenv("CLAUDE_CODE_SHELL", "/usr/bin/zsh")
	stdout.Reset()
	start(t, &stdout, &stderr)
	if out := stdout.String(); !strings.Contains(out, "In zsh:\n- ") {
		t.Errorf("session-start in zsh = %q; want the zsh rules", out)
	}
	// Without principles, the rules for every task aren't printed.
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("guidelines:\n  go: true\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	stdout.Reset()
	start(t, &stdout, &stderr)
	if out := stdout.String(); strings.Contains(out, "On every task") || !strings.Contains(out, "go.md") {
		t.Errorf("session-start with go alone = %q; want go.md and no rules for every task", out)
	}
	// Without the plugin's folder, no Guideline can be named: one problem.
	t.Setenv("CLAUDE_PLUGIN_ROOT", "")
	stdout.Reset()
	start(t, &stdout, &stderr)
	if want := "baloo:\ncould not name the guidelines: CLAUDE_PLUGIN_ROOT is not set\n"; stdout.String() != want {
		t.Errorf("session-start without CLAUDE_PLUGIN_ROOT = %q; want %q", stdout.String(), want)
	}
}

// The Read Hook allows a Guideline file, and says nothing of any other file or call.
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

// condenseProject is a project folder, the folder commands run in until the test ends, whose
// Transcripts, in Claude Code's config folder, are the sessions "one" and "two", "two" the newer.
func condenseProject(t *testing.T) (project, transcripts string) {
	t.Helper()
	config := t.TempDir()
	t.Setenv("CLAUDE_CONFIG_DIR", config)
	project, _ = filepath.EvalSymlinks(t.TempDir())
	t.Chdir(project)
	transcripts = filepath.Join(config, "projects", regexp.MustCompile(`[^A-Za-z0-9]`).ReplaceAllString(project, "-"))
	if err := os.MkdirAll(transcripts, 0o755); err != nil {
		t.Fatal(err)
	}
	for i, id := range []string{"one", "two"} {
		path := filepath.Join(transcripts, id+".jsonl")
		line := `{"type":"user","message":{"content":"prompt of ` + id + ` with AKIA` + `IOSFODNN7EXAMPLE"}}` + "\n" // cspell:disable-line
		if err := os.WriteFile(path, []byte(line), 0o644); err != nil {
			t.Fatal(err)
		}
		when := time.Now().Add(time.Duration(i-2) * time.Hour)
		if err := os.Chtimes(path, when, when); err != nil {
			t.Fatal(err)
		}
	}
	return project, transcripts
}

// condense prints the latest session, the latest few with a summary, the sessions named, or the
// lines around a moment of one, all masked.
func TestCondense(t *testing.T) {
	_, transcripts := condenseProject(t)
	one := "# Session one\n, 0 min, 0 tool calls, 0 failed\nTools: none\n\n[1] prompt: prompt of one with *****\n"
	two := "# Session two\n, 0 min, 0 tool calls, 0 failed\nTools: none\n\n[1] prompt: prompt of two with *****\n"
	summary := "\n# Across 2 sessions\n"
	for _, tc := range []struct {
		args []string
		want string
	}{
		{nil, two},
		{[]string{"--last", "5"}, two + "\n" + one + summary},
		{[]string{"one"}, one},
		{[]string{filepath.Join(transcripts, "one.jsonl"), "two"}, one + "\n" + two + summary},
		{[]string{"two", "--around", "1"}, "[1] user: prompt of two with *****\n"},
	} {
		var stdout, stderr bytes.Buffer
		code := run(append([]string{"condense"}, tc.args...), nil, &stdout, &stderr)
		if code != 0 || stdout.String() != tc.want || stderr.Len() != 0 {
			t.Errorf("condense %q = %d, %q, %q; want 0, %q", tc.args, code, stdout.String(), stderr.String(), tc.want)
		}
	}
	var stdout, stderr bytes.Buffer
	if code := run([]string{"condense", "nope"}, nil, &stdout, &stderr); code != 1 ||
		!strings.HasPrefix(stderr.String(), "baloo condense: ") {
		t.Errorf("condense of a session not there = %d, %q; want 1 and why", code, stderr.String())
	}
}

// Without the project's Transcripts, condense says where it looked.
func TestCondense_WithoutTranscripts(t *testing.T) {
	t.Setenv("CLAUDE_CONFIG_DIR", t.TempDir())
	t.Chdir(t.TempDir())
	var stdout, stderr bytes.Buffer
	if code := run([]string{"condense"}, nil, &stdout, &stderr); code != 1 ||
		!strings.HasPrefix(stderr.String(), "baloo condense: no sessions of ") {
		t.Errorf("condense without Transcripts = %d, %q; want 1 and why", code, stderr.String())
	}
}

// A session that ends in a repo whose Config turns the Session review on starts one, and the next
// session start says what it replied.
func TestSessionEnd(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("session-review: true\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Setenv("CLAUDE_PLUGIN_DATA", t.TempDir())
	bin := t.TempDir()
	if err := os.WriteFile(filepath.Join(bin, "claude"), []byte("#!/bin/sh\ncat >/dev/null\necho 'Added Order to the glossary.'\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", bin+string(os.PathListSeparator)+os.Getenv("PATH"))
	transcript := filepath.Join(t.TempDir(), "s.jsonl")
	if err := os.WriteFile(transcript, []byte(`{"type":"user","message":{"content":"`+strings.Repeat("x", 3000)+`"}}`+"\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	in := `{"transcript_path":"` + transcript + `","cwd":"` + dir + `"}`
	var stdout, stderr bytes.Buffer
	if code := run([]string{"session-end"}, strings.NewReader(in), &stdout, &stderr); code != 0 ||
		stdout.Len() != 0 || stderr.Len() != 0 {
		t.Fatalf("session-end = %d, %q, %q; want 0 and nothing said", code, stdout.String(), stderr.String())
	}
	for deadline := time.Now().Add(5 * time.Second); ; time.Sleep(20 * time.Millisecond) {
		stdout.Reset()
		if code := start(t, &stdout, &stderr); code != 0 {
			t.Fatalf("session-start = %d, %q", code, stderr.String())
		}
		if !strings.Contains(stdout.String(), "still running") || time.Now().After(deadline) {
			break
		}
	}
	if got := stdout.String(); !strings.Contains(got, "\nthe Session review of the last session (") ||
		!strings.Contains(got, ") replied as below: tell the user") ||
		!strings.Contains(got, "\n  Added Order to the glossary.\n") {
		t.Errorf("session-start after a Session review = %q; want what it replied", got)
	}
	// Its own end, and a Config that doesn't turn it on, start none.
	for _, env := range []string{"1", ""} {
		t.Setenv(review.Env, env)
		if env == "" {
			os.WriteFile(filepath.Join(dir, names.Config), []byte("session-review: false\n"), 0o644)
		}
		stdout.Reset()
		run([]string{"session-end"}, strings.NewReader(in), &stdout, &stderr)
		start(t, &stdout, &stderr)
		if strings.Contains(stdout.String(), "Session review") {
			t.Errorf("session-start after a session-end with %s=%q = %q; want no review", review.Env, env, stdout.String())
		}
	}
}

// The Stop check hands a failure of the Config's command back to Claude, once a turn, after a
// prompt and a change; in a Session review's session it runs nothing.
func TestStopCheck(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("stop-check: echo broken; exit 1\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	turn := func(env string, stopActive bool) (string, string) {
		t.Helper()
		t.Setenv(review.Env, env)
		var stdout, stderr bytes.Buffer
		if code := run([]string{"user-prompt-submit"}, strings.NewReader(`{"session_id":"s1"}`), &stdout, &stderr); code != 0 ||
			stdout.Len() != 0 {
			t.Fatalf("user-prompt-submit = %d, %q, %q; want 0 and nothing said", code, stdout.String(), stderr.String())
		}
		if err := os.WriteFile(filepath.Join(dir, "a"), []byte(time.Now().String()), 0o644); err != nil {
			t.Fatal(err)
		}
		stdout.Reset()
		in := `{"session_id":"s1","stop_hook_active":` + strconv.FormatBool(stopActive) + `}`
		if code := run([]string{"stop"}, strings.NewReader(in), &stdout, &stderr); code != 0 {
			t.Fatalf("stop = %d, %q", code, stderr.String())
		}
		return stdout.String(), stderr.String()
	}
	var out struct{ Decision, Reason string }
	got, _ := turn("", false)
	if err := json.Unmarshal([]byte(got), &out); err != nil || out.Decision != "block" ||
		out.Reason != "baloo:stop-check: `echo broken; exit 1` failed with exit status 1:\nbroken\n"+
			"Fix it before you finish, or tell the user why it can't pass." {
		t.Errorf("stop after a change = %q; want it blocked with the failure", got)
	}
	if got, errs := turn("", true); got != "" || errs != "" {
		t.Errorf("stop after a block = %q, %q; want nothing", got, errs)
	}
	if got, errs := turn("1", false); got != "" || errs != "" {
		t.Errorf("stop in a Session review = %q, %q; want nothing", got, errs)
	}
}

// Format on edit runs the Config's command on a file Claude edited in the repo, with its path, and
// says nothing of how it went; a file outside the repo, or a Session review's edit, runs nothing.
func TestFormatOnEdit(t *testing.T) {
	dir := inRepo(t)
	if err := os.MkdirAll(filepath.Join(dir, ".claude", "src"), 0o755); err != nil {
		t.Fatal(err)
	}
	config := "format-on-edit: printf formatted >\n"
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte(config), 0o644); err != nil {
		t.Fatal(err)
	}
	edit := func(path string) {
		t.Helper()
		if err := os.WriteFile(path, []byte("edited"), 0o644); err != nil {
			t.Fatal(err)
		}
		in, _ := json.Marshal(map[string]any{"tool_name": "Edit", "tool_input": map[string]string{"file_path": path}})
		var stdout, stderr bytes.Buffer
		if code := run([]string{"post-tool-use"}, bytes.NewReader(in), &stdout, &stderr); code != 0 ||
			stdout.Len() != 0 || stderr.Len() != 0 {
			t.Errorf("post-tool-use on %s = %d, %q, %q; want 0 and nothing said", path, code, stdout.String(), stderr.String())
		}
	}
	content := func(path string) string {
		t.Helper()
		got, _ := os.ReadFile(path)
		return string(got)
	}
	inside, outside := filepath.Join(dir, ".claude", "src", "a.vue"), filepath.Join(t.TempDir(), "b.vue")
	edit(inside)
	edit(outside)
	if content(inside) != "formatted" || content(outside) != "edited" {
		t.Errorf("after the edits, %q and %q; want the repo's file formatted, the other not", content(inside), content(outside))
	}
	t.Setenv(review.Env, "1")
	edit(inside)
	if content(inside) != "edited" {
		t.Errorf("after a Session review's edit, %q; want it left as edited", content(inside))
	}
	t.Setenv(review.Env, "")
	if err := os.WriteFile(filepath.Join(dir, names.Config), []byte("format-on-edit: exit 3\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	edit(inside) // a failing command is said nothing of, too
}
