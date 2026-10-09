package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"text/tabwriter"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/githooks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/guidelines"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// doctor shows the plugin's state in the repo it runs in, its problems first, each with what fixes
// it (ADR doctor): the binary and the link the Git hooks run, the Config's settings, the Session
// review's Proposals, each Check on or off and why, the Git hooks and the Guidelines. It changes nothing, for session start does the
// fixing, and fails when it finds a problem.
func doctor(stdout, stderr io.Writer) int {
	dir, err := project()
	if err != nil {
		fmt.Fprintf(stderr, "%s: %v\n", names.Plugin, err)
		return 1
	}
	c, path, problems := config.Inspect(dir)
	problems = append(problems, c.Removed...)
	data := os.Getenv("CLAUDE_PLUGIN_DATA")
	var body strings.Builder
	w := tabwriter.NewWriter(&body, 0, 0, 2, ' ', 0)

	exe, _ := os.Executable()
	exe = resolved(exe)
	fmt.Fprintf(w, "\nBinary:\n  running\t%s (%s)\n", exe, version)
	link := ""
	if data == "" {
		problems = append(problems, "CLAUDE_PLUGIN_DATA is not set, so the link the Git hooks "+
			"run can't be checked: run doctor through the Loader, as the doctor skill does")
	} else {
		link = filepath.Join(data, names.Plugin)
		target, err := filepath.EvalSymlinks(link)
		switch {
		case err != nil:
			fmt.Fprintf(w, "  link\t%s, missing\n", link)
			problems = append(problems, fmt.Sprintf("%s is missing, so the Git hooks and the "+
				"Status line run nothing: the next session start points it at this binary", link))
		default:
			fmt.Fprintf(w, "  link\t%s -> %s\n", link, target)
			if target != exe {
				problems = append(problems, fmt.Sprintf("%s points at %s, not at this binary, so "+
					"the Git hooks and the Status line run that one: the next session start "+
					"points it here", link, target))
			}
		}
	}

	switch {
	case c.Root == "":
		fmt.Fprintf(w, "\nConfig: none, outside a repo or in Claude Code's own folder, so every "+
			"setting has its default\n")
	case path == "":
		fmt.Fprintf(w, "\nConfig: none in %s, so every setting has its default: the next "+
			"session start creates %s\n", c.Root, names.Config)
	default:
		fmt.Fprintf(w, "\nConfig: %s\n", path)
	}
	statusLine := "not set"
	if c.StatusLine != nil {
		statusLine = fmt.Sprint(*c.StatusLine)
	}
	for _, s := range [][2]string{
		{"output-style", orNone(c.OutputStyle)},
		{"status-line", statusLine},
		{"session-review", fmt.Sprint(c.SessionReview)},
		{"format-on-edit", orNone(c.FormatOnEdit)},
	} {
		fmt.Fprintf(w, "  %s\t%s\n", s[0], s[1])
	}

	if c.Root != "" {
		var waiting, mismatches int
		for _, it := range review.Items(c.Root, data) {
			switch {
			case it.Mismatch != "":
				mismatches++
				problems = append(problems, fmt.Sprintf("%s%s.md, %s: %s: fix the file, or log "+
					"the decision when the next session asks", names.Proposals, it.Review, it.ID, it.Mismatch))
			case it.Pending():
				waiting++
			}
		}
		fmt.Fprintf(w, "\nSession review:\n  running\t%t\n  proposals waiting\t%d\n  mismatches\t%d\n",
			review.Running(c.Root, data), waiting, mismatches)
	}

	for _, group := range []struct {
		title  string
		checks []string
	}{
		{"Checks in Claude Code's hooks (claude-hooks):", checks.HookChecks},
		{"Checks in Git hooks (git-hooks):", checks.GitHookChecks},
	} {
		fmt.Fprintf(w, "\n%s\n", group.title)
		for _, name := range slices.Sorted(slices.Values(group.checks)) {
			state := "off"
			if c.CheckOn(name) {
				state = "on"
			}
			if _, set := c.Checks[name]; !set {
				state += ", by default"
			}
			fmt.Fprintf(w, "  %s\t%s\n", name, state)
		}
	}

	if c.Root != "" {
		hooksDir, husky, hooks, err := githooks.Inspect(c.Root, data, c.GitHookRuns)
		if err != nil {
			problems = append(problems, fmt.Sprintf("could not read the Git hooks: %v", err))
		} else {
			problems = append(problems, gitHookProblems(hooks, link)...)
			via := ""
			if husky {
				via = ", run by husky 9"
			}
			fmt.Fprintf(w, "\nGit hooks in %s%s:\n", hooksDir, via)
			for _, h := range hooks {
				fmt.Fprintf(w, "  %s\t%s", h.Name, h.State)
				if len(h.Runs) > 0 {
					fmt.Fprintf(w, ": %s", strings.Join(h.Runs, ", "))
				}
				fmt.Fprintln(w)
			}
		}
	}

	var on, off []string
	for _, name := range guidelines.Names() {
		if c.Guidelines[name] {
			on = append(on, name)
		} else {
			off = append(off, name)
		}
	}
	slices.Sort(on)
	slices.Sort(off)
	fmt.Fprintf(w, "\nGuidelines:\n  on\t%s\n  off\t%s\n", orNone(strings.Join(on, ", ")),
		orNone(strings.Join(off, ", ")))
	w.Flush()

	fmt.Fprintf(stdout, "%s %s doctor in %s\n\n", names.Plugin, version, dir)
	if len(problems) == 0 {
		fmt.Fprintln(stdout, "No problems.")
	} else {
		fmt.Fprintln(stdout, "Problems:")
		for _, p := range problems {
			fmt.Fprintf(stdout, "- %s\n", oneLine(p))
		}
	}
	io.WriteString(stdout, body.String())
	if len(problems) > 0 {
		return 1
	}
	return 0
}

// gitHookProblems are the problems of the Git hooks `hooks`, which the plugin points at the binary
// through `link`, each with what fixes it.
func gitHookProblems(hooks []githooks.Hook, link string) []string {
	var problems []string
	for _, h := range hooks {
		checks := strings.Join(h.Runs, ", ")
		switch h.State {
		case githooks.Missing:
			problems = append(problems, fmt.Sprintf("%s is missing, so %s don't run: the next "+
				"session start writes it", h.Path, checks))
		case githooks.Theirs:
			problems = append(problems, fmt.Sprintf("%s is not the plugin's Git hook, so %s don't "+
				"run: move it out of the way and start a session, or turn their keys in %s off",
				h.Path, checks, names.Config))
		case githooks.Outdated:
			if link != "" && h.Bin != link {
				problems = append(problems, fmt.Sprintf("%s runs %s, not %s: the next session "+
					"start rewrites it", h.Path, h.Bin, link))
			} else {
				problems = append(problems, fmt.Sprintf("%s is not as this version writes it: "+
					"the next session start rewrites it", h.Path))
			}
		case githooks.Leftover:
			problems = append(problems, fmt.Sprintf("%s is the plugin's, but %s turns its "+
				"checks and command off: the next session start takes it out", h.Path, names.Config))
		}
		if h.HuskyOutdated {
			problems = append(problems, fmt.Sprintf(".husky/%s is not as session start keeps "+
				"its line that runs the plugin's Git hook: the next session start fixes it, and "+
				"the change is yours to commit", h.Name))
		}
	}
	return problems
}

// resolved is the path `p` with its links followed, or `p` where they can't be.
func resolved(p string) string {
	if r, err := filepath.EvalSymlinks(p); err == nil {
		return r
	}
	return p
}

// orNone is `s`, or "none" where it is empty.
func orNone(s string) string {
	if s == "" {
		return "none"
	}
	return s
}
