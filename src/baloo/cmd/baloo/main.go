// Command baloo is the plugin's binary: a subcommand for each part of the plugin.
package main

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"unicode"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/outputstyle"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// version is set when a Release is built (`-X main.version=…`); a binary built from source
// says "dev".
var version = "dev"

const usage = "usage: baloo version | session-start"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 1 {
		switch args[0] {
		case "version":
			fmt.Fprintln(stdout, version)
			return 0
		case "session-start":
			return sessionStart(stdout, stderr)
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
// Claude Code's settings pick none (ADR output-styles). What it prints Claude Code adds to
// Claude's context, so it prints only what Claude should know: a Config it created, an Output
// style it picked, and the problems, each on one line.
func sessionStart(stdout, stderr io.Writer) int {
	dir, err := project()
	if err != nil {
		fmt.Fprintf(stderr, "baloo: %v\n", err)
		return 1
	}
	c, created, problems := config.Load(dir)
	var report []string
	if created != "" {
		report = append(report, fmt.Sprintf("created %s with every check on: tell the user, "+
			"and that the file is theirs to commit and to change", created))
	}
	if c.OutputStyle != "" {
		picked, err := outputstyle.Pick(dir, c.Root, c.OutputStyle)
		if picked.Path != "" {
			line := fmt.Sprintf("picked the %s:%s output style in %s: tell the user, that it "+
				"applies from their next message or session, and that to drop it they set "+
				"output-style: false in %s and pick another style, Default too, with /output-style",
				names.Plugin, c.OutputStyle, picked.Path, names.Config)
			if picked.Enabled == outputstyle.Project {
				line += "; the change to the team's settings is theirs to commit"
			}
			report = append(report, line)
		}
		if err != nil {
			problems = append(problems, fmt.Sprintf("could not pick the %s:%s output style: %v",
				names.Plugin, c.OutputStyle, err))
		}
	}
	if report = append(report, problems...); len(report) > 0 {
		for i, line := range report {
			report[i] = oneLine(line)
		}
		fmt.Fprintf(stdout, "baloo:\n%s\n", strings.Join(report, "\n"))
	}
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
