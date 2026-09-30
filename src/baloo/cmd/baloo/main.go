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
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/statusline"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// version is set when a Release is built (`-X main.version=…`); a binary built from source
// says "dev".
var version = "dev"

const usage = "usage: baloo version | session-start | allow-guideline | status-line |\n" +
	"  check no-ai-coauthor|conventional-commits <message file> |\n" +
	"  check no-secrets | check linear-history < <pushed refs>"

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
		}
	}
	if len(args) == 3 && args[0] == "check" && commitMessage[args[1]] != nil {
		return checkCommitMessage(args[1], args[2], stderr)
	}
	if len(args) == 2 && args[0] == "check" && args[1] == "no-secrets" {
		return noSecrets(stderr)
	}
	if len(args) == 2 && args[0] == "check" && args[1] == "linear-history" {
		return linearHistory(stdin, stderr)
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
// Claude should know: a Config it created, an Output style or a Status line it set, and the
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
		shown, err := statusline.Sync(dir, c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), *c.StatusLine)
		if shown {
			report = append(report, fmt.Sprintf("set the %s status line in %s: tell the user, that "+
				"it shows from their next message, and that status-line: false in %s takes it out",
				names.Plugin, filepath.Join(dir, names.LocalSettings), names.Config))
		}
		if err != nil {
			problems = append(problems, fmt.Sprintf("could not set the status line: %v", err))
		}
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

// commitMessage are the commit-msg hook's Checks, by name: each says what is wrong with a commit
// message, or "" when nothing is.
var commitMessage = map[string]func(message string) string{
	"no-ai-coauthor": func(message string) string {
		if found := checks.NoAICoauthor(message); len(found) > 0 {
			return "remove the AI co-author or credit:\n" + strings.Join(found, "\n")
		}
		return ""
	},
	"conventional-commits": checks.ConventionalCommit,
}

// checkCommitMessage runs the commit-msg Check `name` on the message in the file `path`: it fails
// with what is wrong, for git to show.
func checkCommitMessage(name, path string, stderr io.Writer) int {
	message, err := os.ReadFile(path)
	if err != nil {
		fmt.Fprintf(stderr, "%s:%s: %v\n", names.Plugin, name, err)
		return 2
	}
	why := commitMessage[name](string(message))
	if why == "" {
		return 0
	}
	fmt.Fprintf(stderr, "%s:%s: %s\n", names.Plugin, name, why)
	return 1
}

// noSecrets is the pre-commit hook's Check baloo:no-secrets on the repo git runs it in: it fails
// with where each Secret the staged changes add is, for git to show, but never the Secret.
func noSecrets(stderr io.Writer) int {
	const name = names.Plugin + ":no-secrets"
	found, err := checks.NoSecrets(".")
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", name, err)
		return 2
	}
	if len(found) == 0 {
		return 0
	}
	fmt.Fprintf(stderr, "%s: remove each secret, or mark a false alarm with %s:\n%s\n",
		name, checks.AllowSecret, strings.Join(found, "\n"))
	return 1
}

// linearHistory is the pre-push hook's Check baloo:linear-history on the repo git runs it in: it
// fails with the merge commits the push sends, from the refs git gives it on stdin.
func linearHistory(stdin io.Reader, stderr io.Writer) int {
	const name = names.Plugin + ":linear-history"
	pushed, err := io.ReadAll(stdin)
	var found []string
	if err == nil {
		found, err = checks.LinearHistory(".", string(pushed))
	}
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", name, err)
		return 2
	}
	if len(found) == 0 {
		return 0
	}
	fmt.Fprintf(stderr, "%s: rebase instead of merging, then push the rebased branch with "+
		"--force-with-lease; merge commits:\n%s\n", name, strings.Join(found, "\n"))
	return 1
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
