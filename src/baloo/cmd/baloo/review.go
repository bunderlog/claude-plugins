package main

import (
	"encoding/json"
	"io"
	"os"
	"os/exec"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/config"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/review"
)

// sessionEnd is the SessionEnd hook's part (ADR session-review): where the repo's Config turns the
// Session review on, it starts one of the session that ended and returns at once. It says nothing
// and never fails the exit: without the Transcript, `claude`, or the plugin's folder or data folder, and in
// a Session review's own session, it does nothing. A problem with the Config is left to the next
// session start, as there is no one to tell now.
func sessionEnd(stdin io.Reader) int {
	var end struct {
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
		review.Start(claude, plugin, c.Root, data, transcript)
	}
	return 0
}
