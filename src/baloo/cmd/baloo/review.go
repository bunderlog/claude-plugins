package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// sessionEnd is the SessionEnd Hook's part (ADR session-review): where the repo's Config turns the
// Session review on, it starts one of the session that ended and returns at once. It says nothing
// and never fails the exit: without the Transcript, `claude`, or the plugin's folder or data
// folder, and in a Session review's own session, it does nothing. A problem with the Config is left
// to the next session start, as there is no one to tell now.
func sessionEnd(stdin io.Reader) int {
	var end struct {
		Session    string `json:"session_id"`
		Transcript string `json:"transcript_path"`
	}
	dir, err := project()
	data, plugin := os.Getenv("CLAUDE_PLUGIN_DATA"), os.Getenv("CLAUDE_PLUGIN_ROOT")
	if os.Getenv(review.Env) != "" || json.NewDecoder(stdin).Decode(&end) != nil || err != nil ||
		data == "" || plugin == "" {
		return 0
	}
	c := config.Read(dir)
	if c.Root == "" || !c.SessionReview {
		return 0
	}
	claude, err := exec.LookPath("claude")
	transcript, err2 := os.ReadFile(end.Transcript)
	if err == nil && err2 == nil {
		review.Start(claude, plugin, c.Root, data, end.Session, transcript)
	}
	return 0
}

// userPromptSubmit is the UserPromptSubmit Hook's part (ADR session-review): it tells Claude of
// the Proposals that came, such as from a Session review that ended after session start, and the
// session hasn't been told of yet. It says nothing else, and nothing in a Session review's session.
func userPromptSubmit(stdin io.Reader, stdout io.Writer) int {
	var prompt struct {
		Session string `json:"session_id"`
	}
	dir, err := project()
	if os.Getenv(review.Env) != "" || json.NewDecoder(stdin).Decode(&prompt) != nil || err != nil {
		return 0
	}
	c := config.Read(dir)
	if c.Root == "" {
		return 0
	}
	lines := review.Show(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), prompt.Session, decideCommand())
	if len(lines) > 0 {
		out := json.NewEncoder(stdout)
		out.SetEscapeHTML(false)
		out.Encode(map[string]any{
			"hookSpecificOutput": map[string]string{
				"hookEventName":     "UserPromptSubmit",
				"additionalContext": names.Plugin + ":\n" + strings.Join(lines, "\n") + "\n",
			},
		})
	}
	return 0
}

// decideCommand is the command Claude runs, in the repo, to log the user's decision on a Proposal:
// the review-decision of the plugin's Loader, which finds the binary in the data folder, as the
// doctor skill runs it.
func decideCommand() string {
	return "CLAUDE_PLUGIN_DATA='" + os.Getenv("CLAUDE_PLUGIN_DATA") + "' sh '" +
		filepath.Join(os.Getenv("CLAUDE_PLUGIN_ROOT"), "scripts", "loader") + "' review-decision"
}

// reviewDecision logs the user's decision on a Proposal, the arguments `args`: its review, its id
// and the decision (ADR session-review). It fails where the decision can't be logged, saying why.
func reviewDecision(args []string, stdout, stderr io.Writer) int {
	dir, err := project()
	if err != nil {
		fmt.Fprintf(stderr, "%s review-decision: %v\n", names.Plugin, err)
		return 1
	}
	c := config.Read(dir)
	if c.Root == "" {
		fmt.Fprintf(stderr, "%s review-decision: %s is not in a repo\n", names.Plugin, dir)
		return 1
	}
	todo, err := review.Decide(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), args[0], args[1], args[2])
	if err != nil {
		fmt.Fprintf(stderr, "%s review-decision: %v\n", names.Plugin, err)
		return 1
	}
	fmt.Fprintf(stdout, "logged %s %s %s\n", args[0], args[1], args[2])
	if todo != "" {
		fmt.Fprintln(stdout, todo)
	}
	return 0
}
