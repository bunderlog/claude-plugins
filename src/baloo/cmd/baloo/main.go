// Command baloo is the plugin's binary: a subcommand for each part of the plugin.
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"maps"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"unicode"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/githooks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/outputstyle"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/statusline"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// version is set when a Release is built (`-X main.version=…`); a binary built from source
// says "dev".
var version = "dev"

var usage = "usage: baloo version | session-start | allow-guideline | subagent-start | status-line |\n" +
	"  pre-tool-use | post-tool-use | session-end | user-prompt-submit | stop |\n  " +
	strings.Join(checks.Usage(), " |\n  ") + " |\n" +
	"  git-hook " + strings.Join(slices.Sorted(maps.Keys(checks.GitHooks)), "|") + " <git's arguments> |\n" +
	"  condense [--last <n> | <session>...] | condense <session> --around <line>"

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

func run(args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	if len(args) == 1 {
		switch args[0] {
		case "version":
			fmt.Fprintln(stdout, version)
			return 0
		case "session-start":
			var context strings.Builder
			code := sessionStart(&context, stderr)
			if code == 0 {
				started(stdout, context.String())
			}
			return code
		case "allow-guideline":
			return allowGuideline(stdin, stdout)
		case "subagent-start":
			return subagentStart(stdin, stdout)
		case "status-line":
			return statusLine(stdin, stdout)
		case "pre-tool-use":
			return preToolUse(stdin, stdout)
		case "post-tool-use":
			return postToolUse(stdin)
		case "session-end":
			return sessionEnd(stdin)
		case "user-prompt-submit":
			return userPromptSubmit(stdin)
		case "stop":
			return stop(stdin, stdout)
		}
	}
	if len(args) > 0 && args[0] == "condense" {
		if code, ok := condenseSessions(args[1:], stdout, stderr); ok {
			return code
		}
	}
	if len(args) > 1 && args[0] == "git-hook" {
		in, on := gitHookInput(stdin)
		if code, ok := checks.RunHook(args[1], args[2:], in, on, stderr); ok {
			return code
		}
	}
	if len(args) > 1 && args[0] == "check" {
		in, on := gitHookInput(stdin)
		if code, ok := checks.Run(args[1], args[2:], in, on, stderr); ok {
			return code
		}
	}
	fmt.Fprintln(stderr, usage)
	return 2
}

// project is the folder Claude Code runs in: a Hook gets it as CLAUDE_PROJECT_DIR, and the
// binary run by hand gets its working folder.
func project() (string, error) {
	if dir := os.Getenv("CLAUDE_PROJECT_DIR"); dir != "" {
		return dir, nil
	}
	return os.Getwd()
}

// report is what session start tells Claude: the lines of what it did, and of what went wrong,
// printed as one list once both are complete.
type report struct{ lines, problems []string }

// ok adds a line of what session start did.
func (r *report) ok(line string) { r.lines = append(r.lines, line) }

// fail adds what went wrong, under `prefix`, when `err` is set.
func (r *report) fail(prefix string, err error) {
	if err != nil {
		r.problems = append(r.problems, fmt.Sprintf("%s: %v", prefix, err))
	}
}

// setting reports the (path, Scope, err) a setting session start wrote returns, as
// outputstyle.Pick and settings.SetUnset do: `line`, with the team-commit suffix where `enabled`
// is Project, when `path` is set; `err` under `errPrefix` otherwise.
func (r *report) setting(path string, enabled settings.Scope, line string, err error, errPrefix string) {
	if path != "" {
		if enabled == settings.Project {
			line += "; the change to the team's settings is theirs to commit"
		}
		r.ok(line)
	}
	r.fail(errPrefix, err)
}

// sessionStart is the SessionStart Hook's part, run once the Loader has the binary: it creates the
// repo's Config when it has none (ADR config), reads it, picks the Output style it names where
// Claude Code's settings pick none (ADR output-styles), turns off Claude Code's commit attribution
// where no-ai-coauthor is on and they set none (ADR checks), sets the Status line or takes it
// out (ADR status-line), and writes the Git hooks or takes them out (ADR git-hooks). What it prints
// Claude Code adds to Claude's context, so it prints only what Claude should know: a Config it
// created, an Output style, an attribution or a Status line it set, the Git hooks it wrote, took
// out, changed in husky or left alone, a Hook Check it turns off (ADR checks), what the last
// Session review replied (ADR session-review), how many items the Inbox holds (ADR inbox), and
// the problems, each on one line; then the Guidelines the Config turns on (ADR guidelines). In a
// Session review's session it only names the Guidelines: that session changes nothing but
// .about/'s glossary, ADRs and Inbox (ADR session-review).
func sessionStart(stdout, stderr io.Writer) int {
	dir, err := project()
	if err != nil {
		fmt.Fprintf(stderr, "baloo: %v\n", err)
		return 1
	}
	if os.Getenv(review.Env) != "" {
		if index, _ := guidelineIndex(config.Read(dir).Guidelines); index != "" {
			fmt.Fprintf(stdout, "%s\n", index)
		}
		return 0
	}
	c, created, problems := config.Load(dir)
	rep := report{problems: problems}
	if created != "" {
		rep.ok(fmt.Sprintf("created %s with every check on and the guidelines "+
			"that fit the repo: tell the user, "+
			"and that the file is theirs to commit and to change", created))
	}
	if c.OutputStyle != "" {
		picked, err := outputstyle.Pick(dir, c.Root, c.OutputStyle)
		line := fmt.Sprintf("picked the %s:%s output style in %s: tell the user, that it "+
			"applies from their next message or session, and that to drop it they set "+
			"output-style: false in %s and pick another style, Default too, with /output-style",
			names.Plugin, c.OutputStyle, picked.Path, names.Config)
		rep.setting(picked.Path, picked.Enabled, line, err,
			fmt.Sprintf("could not pick the %s:%s output style", names.Plugin, c.OutputStyle))
	}
	if c.Root != "" && c.CheckOn("no-ai-coauthor") {
		path, enabled, err := settings.SetUnset(dir, c.Root,
			[]string{"attribution", "includeCoAuthoredBy"}, "attribution", map[string]string{"commit": ""})
		line := fmt.Sprintf("turned off Claude Code's commit attribution in %s, since "+
			"git-hooks.no-ai-coauthor in %s rejects it: tell the user", path, names.Config)
		rep.setting(path, enabled, line, err, "could not turn off the commit attribution")
	}
	if c.Root != "" && c.StatusLine != nil {
		shown, err := statusline.Set(dir, c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), *c.StatusLine)
		if shown {
			rep.ok(fmt.Sprintf("set the %s status line in %s: tell the user, that "+
				"it shows from their next message, and that status-line: false in %s takes it out",
				names.Plugin, filepath.Join(dir, names.LocalSettings), names.Config))
		}
		rep.fail("could not set the status line", err)
	}
	if c.Root != "" {
		r, err := githooks.Write(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), c.CheckOn)
		rep.lines = append(rep.lines, gitHooksReport(r)...)
		rep.fail("could not write the Git hooks", err)
	}
	for _, name := range checks.HookChecks {
		if on, ok := c.Checks[name]; ok && !on {
			rep.ok(fmt.Sprintf("claude-hooks.%s: false in %s turns off a check in Claude "+
				"Code's hooks: tell the user", name, names.Config))
		}
	}
	if c.Root != "" {
		rep.lines = append(rep.lines, review.Last(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"))...)
		if n, kept := inboxItems(c.Root); n > 0 {
			items := "items"
			if n == 1 {
				items = "item"
			}
			left := ""
			switch {
			case kept == n:
				left = ", each gone through once and kept"
			case kept > 0:
				left = fmt.Sprintf(", %d not gone through yet", n-kept)
			}
			rep.ok(fmt.Sprintf("%s holds %d %s to consider%s: tell the user, and that "+
				"/%s:inbox goes through them", names.Inbox, n, items, left, names.Plugin))
		}
	}
	index, err := guidelineIndex(c.Guidelines)
	rep.fail("could not name the guidelines", err)
	if lines := append(rep.lines, rep.problems...); len(lines) > 0 {
		for i, line := range lines {
			lines[i] = oneLine(line)
		}
		fmt.Fprintf(stdout, "baloo:\n%s\n", strings.Join(lines, "\n"))
	}
	if index != "" {
		fmt.Fprintf(stdout, "%s\n", index)
	}
	return 0
}

// started writes the SessionStart Hook's JSON: what session start tells Claude, `context`, which
// Claude Code adds to Claude's context, and the plugin's version, which it shows the user, so
// they can see which Release runs.
func started(stdout io.Writer, context string) {
	out := map[string]any{"systemMessage": names.Plugin + " " + version}
	if context != "" {
		out["hookSpecificOutput"] = map[string]string{
			"hookEventName":     "SessionStart",
			"additionalContext": context,
		}
	}
	json.NewEncoder(stdout).Encode(out)
}

// gitHooksReport is what Claude is told of the Git hooks session start wrote, took out or left
// alone (ADR git-hooks).
func gitHooksReport(r githooks.Report) []string {
	var lines []string
	if len(r.Written) > 0 {
		lines = append(lines, fmt.Sprintf("wrote the Git hooks %s in %s, which run the plugin's checks "+
			"on every commit and push: tell the user, and that a check's key under git-hooks in %s "+
			"turns it off", strings.Join(r.Written, ", "), r.Dir, names.Config))
	}
	if len(r.Removed) > 0 {
		lines = append(lines, fmt.Sprintf("took out the Git hooks %s in %s, whose checks %s turns off: "+
			"tell the user", strings.Join(r.Removed, ", "), r.Dir, names.Config))
	}
	if len(r.Husky) > 0 {
		lines = append(lines, fmt.Sprintf("changed %s, husky's Git hooks, to run the plugin's where their "+
			"checks are on: tell the user, and that the change is theirs to commit", strings.Join(r.Husky, ", ")))
	}
	for _, b := range r.Theirs {
		lines = append(lines, fmt.Sprintf("%s is not the plugin's Git hook, so %s don't run: tell the user, "+
			"and that their keys under git-hooks in %s, turned off, end this line",
			b.Path, strings.Join(b.Checks, ", "), names.Config))
	}
	return lines
}

// keptMark ends the date line of an Inbox item the user went through once and kept (ADR inbox).
var keptMark = regexp.MustCompile(` · kept \d{4}-\d{2}-\d{2}\s*$`)

// inboxItems is how many items the Inbox of the repo at `root` holds, one per `## ` heading
// outside a fenced code block, and how many of them are kept (ADR inbox); 0 without one.
func inboxItems(root string) (n, kept int) {
	text, err := os.ReadFile(filepath.Join(root, names.Inbox))
	if err != nil {
		return 0, 0
	}
	fenced, dated := false, true
	for _, line := range strings.Split(string(text), "\n") {
		switch {
		case strings.HasPrefix(line, "```"):
			fenced, dated = !fenced, true
		case fenced:
		case strings.HasPrefix(line, "## "):
			n++
			dated = false
		case !dated && strings.TrimSpace(line) != "":
			// The first line after the heading is the item's date line.
			dated = true
			if keptMark.MatchString(line) {
				kept++
			}
		}
	}
	return n, kept
}

// guidelineIndex is what Claude is told of the Guidelines `on`, in the plugin's folder that Claude
// Code gives a Hook as CLAUDE_PLUGIN_ROOT, for the Bash tool's shell: CLAUDE_CODE_SHELL, or the
// user's SHELL.
func guidelineIndex(on map[string]bool) (string, error) {
	plugin, shell := os.Getenv("CLAUDE_PLUGIN_ROOT"), os.Getenv("CLAUDE_CODE_SHELL")
	if shell == "" {
		shell = os.Getenv("SHELL")
	}
	index, err := guidelines.Index(plugin, on, filepath.Base(shell))
	if index != "" && plugin == "" {
		return "", errors.New("CLAUDE_PLUGIN_ROOT is not set")
	}
	return index, err
}

// allowGuideline is the Read tool's PreToolUse Hook (ADR guidelines): it allows reading a
// Guideline file of the plugin without asking the user, whose own deny and ask rules still win,
// and says nothing of any other file. It never stops a Read: whatever goes wrong, it says nothing.
func allowGuideline(stdin io.Reader, stdout io.Writer) int {
	var call struct {
		ToolName  string `json:"tool_name"`
		ToolInput struct {
			FilePath string `json:"file_path"`
		} `json:"tool_input"`
	}
	if json.NewDecoder(stdin).Decode(&call) != nil || call.ToolName != "Read" ||
		!guidelines.Readable(os.Getenv("CLAUDE_PLUGIN_ROOT"), call.ToolInput.FilePath) {
		return 0
	}
	json.NewEncoder(stdout).Encode(map[string]any{"hookSpecificOutput": map[string]string{
		"hookEventName":            "PreToolUse",
		"permissionDecision":       "allow",
		"permissionDecisionReason": names.Plugin + ": one of the plugin's own guidelines",
	}})
	return 0
}

// subagentStart is the SubagentStart Hook of the plugin's verifier (ADR verify): it tells the
// agent, which session start's context doesn't reach, the Guidelines the Config turns on, as
// session start names them. For another agent, or with none on, it says nothing.
func subagentStart(stdin io.Reader, stdout io.Writer) int {
	var call struct {
		AgentType string `json:"agent_type"`
	}
	if json.NewDecoder(stdin).Decode(&call) != nil || call.AgentType != names.Verifier {
		return 0
	}
	dir, err := project()
	if err != nil {
		return 0
	}
	index, _ := guidelineIndex(config.Read(dir).Guidelines)
	if index == "" {
		return 0
	}
	json.NewEncoder(stdout).Encode(map[string]any{"hookSpecificOutput": map[string]string{
		"hookEventName":     "SubagentStart",
		"additionalContext": index,
	}})
	return 0
}

// statusLine is Claude Code's status line command (ADR status-line): it prints the Status line for
// what Claude Code gives it on stdin, in a terminal as wide as COLUMNS says. A field of another
// type than the plugin's is left out, and the rest shows; whatever else goes wrong, it prints
// nothing, since Claude Code shows under the prompt whatever it prints.
func statusLine(stdin io.Reader, stdout io.Writer) int {
	var in statusline.Input
	var typeErr *json.UnmarshalTypeError
	if err := json.NewDecoder(stdin).Decode(&in); err != nil && !errors.As(err, &typeErr) {
		return 0
	}
	columns, err := strconv.Atoi(os.Getenv("COLUMNS"))
	if err != nil || columns <= 0 {
		columns = 120
	}
	fmt.Fprintln(stdout, statusline.Render(in, statusline.Branch(in.Workspace.CurrentDir), columns))
	return 0
}

// oneLine escapes what isn't printable in `s`, as Go does in a string literal, so a line that
// carries a repo's key or path stays one line: a newline in them can't start a line of its own
// that passes for the plugin's.
func oneLine(s string) string {
	var b strings.Builder
	for _, r := range s {
		if unicode.IsPrint(r) {
			b.WriteRune(r)
		} else {
			q := strconv.QuoteRune(r)
			b.WriteString(q[1 : len(q)-1])
		}
	}
	return b.String()
}
