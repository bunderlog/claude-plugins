package main

import (
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/condense"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// aroundLines is how many lines either side of a moment condense --around shows.
const aroundLines = 5

// condenseSessions is the retro skill's condense (ADR transcripts): the Transcripts of the project
// in the folder it runs in, condensed and masked. With no `args`, the latest session worth a
// Retro; `--last <n>`, the latest n; session ids or Transcript files, those; with more than one,
// a summary across them too. `<session> --around <line>` is the lines around one moment. It
// returns ok false for arguments it can't read.
func condenseSessions(args []string, stdout, stderr io.Writer) (code int, ok bool) {
	fail := func(err error) (int, bool) {
		fmt.Fprintf(stderr, "%s condense: %v\n", names.Plugin, err)
		return 1, true
	}
	cwd, err := os.Getwd()
	if err != nil {
		return fail(err)
	}
	config := settings.Own()
	if config == "" {
		return fail(errors.New("found neither CLAUDE_CONFIG_DIR nor a home folder"))
	}
	dir := condense.Dir(config, cwd)
	file := func(session string) string {
		if _, err := os.Stat(session); err == nil || dir == "" {
			return session
		}
		return filepath.Join(dir, strings.TrimSuffix(filepath.Base(session), ".jsonl")+".jsonl")
	}
	if len(args) == 3 && args[1] == "--around" {
		at, err := strconv.Atoi(args[2])
		if err != nil {
			return 0, false
		}
		text, err := os.ReadFile(file(args[0]))
		if err != nil {
			return fail(err)
		}
		fmt.Fprintln(stdout, condense.Around(text, at, aroundLines))
		return 0, true
	}
	var sessions []condense.Session
	switch {
	case len(args) == 0 || args[0] == "--last":
		n := 1
		if len(args) > 0 {
			if n, err = strconv.Atoi(strings.Join(args[1:], " ")); err != nil || n < 1 {
				return 0, false
			}
		}
		if dir != "" {
			if sessions, err = condense.Latest(dir, n); err != nil {
				return fail(err)
			}
		}
		if len(sessions) == 0 {
			return fail(errors.New("no sessions of " + cwd + " in " + filepath.Join(config, "projects")))
		}
	default:
		for _, session := range args {
			s, err := condense.Read(file(session))
			if err != nil {
				return fail(err)
			}
			sessions = append(sessions, s)
		}
	}
	var parts []string
	for _, s := range sessions {
		parts = append(parts, s.Report())
	}
	if len(sessions) > 1 {
		parts = append(parts, condense.Summary(sessions))
	}
	fmt.Fprintln(stdout, strings.Join(parts, "\n\n"))
	return 0, true
}
