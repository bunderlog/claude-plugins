package main

import (
	"encoding/json"
	"io"
	"os"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/stopcheck"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// turn is what Claude Code gives the UserPromptSubmit and Stop Hooks.
type turn struct {
	Session    string `json:"session_id"`
	StopActive bool   `json:"stop_hook_active"`
}

// stopCheckConfig is the repo's Config where the Stop check runs (ADR stop-check): a Config that
// names its command, outside a Session review's session; ok is false elsewhere.
func stopCheckConfig(stdin io.Reader) (t turn, c config.Config, ok bool) {
	dir, err := project()
	if os.Getenv(review.Env) != "" || err != nil || json.NewDecoder(stdin).Decode(&t) != nil {
		return t, c, false
	}
	c = config.Read(dir)
	return t, c, c.Root != "" && c.StopCheck != ""
}

// userPromptSubmit is the UserPromptSubmit Hook's part of the Stop check: it marks the working
// tree for the turn's Stop. It says nothing, for Claude Code adds what it prints to the prompt,
// and never fails the prompt.
func userPromptSubmit(stdin io.Reader) int {
	if t, c, ok := stopCheckConfig(stdin); ok {
		stopcheck.Mark(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), t.Session)
	}
	return 0
}

// stop is the Stop Hook's part of the Stop check: after a turn that changed the working tree, it
// runs the Config's command and, when it fails, keeps Claude from stopping with what it printed.
// The Stop after such a block passes, so Claude is kept at most once a turn.
func stop(stdin io.Reader, stdout io.Writer) int {
	t, c, ok := stopCheckConfig(stdin)
	if !ok || t.StopActive {
		return 0
	}
	failure, err := stopcheck.Check(c.Root, os.Getenv("CLAUDE_PLUGIN_DATA"), t.Session, c.StopCheck)
	if err != nil || failure == "" {
		return 0
	}
	json.NewEncoder(stdout).Encode(map[string]string{"decision": "block",
		"reason": names.Plugin + ":stop-check: " + failure +
			"Fix it before you finish, or tell the user why it can't pass."})
	return 0
}
