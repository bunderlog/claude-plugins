// Command baloo is the plugin's binary: a subcommand for each part of the plugin.
package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unicode"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
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

const usage = "usage: baloo version | session-start | allow-guideline | status-line |\n" +
	"  pre-tool-use | session-end |\n" +
	"  check no-ai-coauthor|conventional-commits <message file> |\n" +
	"  check no-secrets-in-commits | check no-stale-adr-date |\n" +
	"  check linear-history < <pushed refs> |\n" +
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
			return sessionStart(stdout, stderr)
		case "allow-guideline":
			return allowGuideline(stdin, stdout)
		case "status-line":
			return statusLine(stdin, stdout)
		case "pre-tool-use":
			return preToolUse(stdin, stdout)
		case "session-end":
			return sessionEnd(stdin)
		}
	}
	if len(args) > 0 && args[0] == "condense" {
		if code, ok := condenseSessions(args[1:], stdout, stderr); ok {
			return code
		}
	}
	if len(args) > 1 && args[0] == "check" {
		if code, ok := check(args[1], args[2:], stdin, stderr); ok {
			return code
		}
	}
	fmt.Fprintln(stderr, usage)
	return 2
}

// project is the folder Claude Code runs in: a hook gets it as CLAUDE_PROJECT_DIR, and the
// binary run by hand gets its working folder.
func project() (string, error) {
	if dir := os.Getenv("CLAUDE_PROJECT_DIR"); dir != "" {
		return dir, nil
	}
	return os.Getwd()
}

// sessionStart is the SessionStart hook's part, run once the Loader has the binary: it creates the
// repo's Config when it has none (ADR config), reads it, and picks the Output style it names where
// Claude Code's settings pick none (ADR output-styles), and sets the Status line or takes it out
// (ADR status-line). What it prints Claude Code adds to Claude's context, so it prints only what
// Claude should know: a Config it created, an Output style or a Status line it set, a Hook Check it
// turns off (ADR checks), what the last Session review replied (ADR session-review), and the
// problems, each on one line; then the Guidelines the Config turns on (ADR guidelines).
func sessionStart(stdout, stderr io.Writer) int {
	dir, err := project()
	if err != nil {
		fmt.Fprintf(stderr, "baloo: %v\n", err)
		return 1
	}
	c, created, problems := config.Load(dir)
	var report []string
	if created != "" {
		report = append(report, fmt.Sprintf("created %s with every check on and the guidelines "+
			"that fit the repo: tell the user, "+
			"and that the file is theirs to commit and to change", created))
	}
	if c.OutputStyle != "" {
		picked, err := outputstyle.Pick(dir, c.Root, c.OutputStyle)
		if picked.Path != "" {
			line := fmt.Sprintf("picked the %s:%s output style in %s: tell the user, that it "+
				"applies from their next message or session, and that to drop it they set "+
				"output-style: false in %s and pick another style, Default too, with /output-style",
				names.Plugin, c.OutputStyle, picked.Path, names.Config)
			if picked.Enabled == settings.Project {
				line += "; the change to the team's settings is theirs to commit"
			}
			report = append(report, line)
		}
		if err != nil {
			problems = append(problems, fmt.Sprintf("could not pick the %s:%s output style: %v",
				names.Plugin, c.OutputStyle, err))
		}
	}
	if c.Root != "" && c.StatusLine != nil {
		shown, err := statusline.Set(dir, c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), *c.StatusLine)
		if shown {
			report = append(report, fmt.Sprintf("set the %s status line in %s: tell the user, that "+
				"it shows from their next message, and that status-line: false in %s takes it out",
				names.Plugin, filepath.Join(dir, names.LocalSettings), names.Config))
		}
		if err != nil {
			problems = append(problems, fmt.Sprintf("could not set the status line: %v", err))
		}
	}
	for _, name := range checks.HookChecks {
		if on, ok := c.Checks[name]; ok && !on {
			report = append(report, fmt.Sprintf("claude-hooks.%s: false in %s turns off a check on Claude's "+
				"tool calls: tell the user", name, names.Config))
		}
	}
	if c.Root != "" {
		report = append(report, review.Last(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"))...)
	}
	index, err := guidelineIndex(c.Guidelines)
	if err != nil {
		problems = append(problems, fmt.Sprintf("could not name the guidelines: %v", err))
	}
	if report = append(report, problems...); len(report) > 0 {
		for i, line := range report {
			report[i] = oneLine(line)
		}
		fmt.Fprintf(stdout, "baloo:\n%s\n", strings.Join(report, "\n"))
	}
	if index != "" {
		fmt.Fprintf(stdout, "%s\n", index)
	}
	return 0
}

// guidelineIndex is what Claude is told of the Guidelines `on`, in the plugin's folder that Claude
// Code gives a hook as CLAUDE_PLUGIN_ROOT.
func guidelineIndex(on map[string]bool) (string, error) {
	plugin := os.Getenv("CLAUDE_PLUGIN_ROOT")
	index, err := guidelines.Index(plugin, on)
	if index != "" && plugin == "" {
		return "", errors.New("CLAUDE_PLUGIN_ROOT is not set")
	}
	return index, err
}

// allowGuideline is the Read tool's PreToolUse hook (ADR guidelines): it allows reading a
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
