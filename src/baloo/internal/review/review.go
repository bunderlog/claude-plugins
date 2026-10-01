// Package review starts the Session review of a session that ended, and says what the last one
// changed (ADR session-review).
package review

// cspell:ignore dont

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/condense"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Env is set in a Session review's environment, so that its own end starts no review.
var Env = strings.ToUpper(names.Plugin) + "_SESSION_REVIEW"

const (
	minChars = 2_000   // a shorter conversation can't have settled a term or a decision
	maxChars = 200_000 // of a longer one, the review reads the end
	reported = 20      // the most lines of a review's reply the next session start shows
)

var prompt = `The conversation that just ended is on stdin. Use the ` + names.Plugin + `:glossary
and ` + names.Plugin + `:adr skills to record in .about/ what it settled that .about/ doesn't say
yet. Nobody can answer questions: record only what the conversation clearly agreed, and only about
this repo. Anything contested or left open, and a bug or problem it found but didn't fix, is an
item in ` + names.Inbox + `: a "## <title>", a line "<YYYY-MM-DD> · session review", then what it
is and what would settle it; create the file, "# Inbox" first, with its first item. Delete an
item there that the conversation settled. Change nothing else, and end with one line per change.`

// files are where the Session review at `root` keeps its reply, after a line with when it
// started, and its process id while it runs, in the plugin's data folder `data`.
func files(root, data string) (reply, pid string) {
	sum := sha256.Sum256([]byte(root))
	reply = filepath.Join(data, "session-review", hex.EncodeToString(sum[:8])+".txt")
	return reply, reply + ".pid"
}

// Start starts the Session review of the session whose Transcript is `transcript`, with the
// `claude` given and the plugin in the folder `plugin`, whose skills it uses, at the repo's root
// `root`, keeping its state in the plugin's data folder `data`.
// It returns once the review runs, detached, and says whether one started: none does for a
// headless session, or one too short to have settled much.
func Start(claude, plugin, root, data string, transcript []byte) (bool, error) {
	if condense.Condense(transcript, "").Headless {
		return false, nil
	}
	conversation := condense.Conversation(transcript, maxChars)
	if len([]rune(conversation)) < minChars {
		return false, nil
	}
	reply, pid := files(root, data)
	if err := os.MkdirAll(filepath.Dir(reply), 0o700); err != nil {
		return false, err
	}
	in, err := os.CreateTemp(filepath.Dir(reply), "conversation-*")
	if err != nil {
		return false, err
	}
	defer os.Remove(in.Name()) // the review keeps its open file
	defer in.Close()
	if _, err := in.WriteString(conversation); err != nil {
		return false, err
	}
	if _, err := in.Seek(0, 0); err != nil {
		return false, err
	}
	if err := os.WriteFile(reply, []byte(time.Now().UTC().Format(time.RFC3339)+"\n"), 0o600); err != nil {
		return false, err
	}
	out, err := os.OpenFile(reply, os.O_WRONLY|os.O_APPEND, 0)
	if err != nil {
		return false, err
	}
	defer out.Close()
	log, err := os.OpenFile(filepath.Join(filepath.Dir(reply), "session-review.log"),
		os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0o600)
	if err != nil {
		return false, err
	}
	defer log.Close()
	fmt.Fprintf(log, "--- %s %s\n", time.Now().UTC().Format(time.RFC3339), root)
	// Only reading and editing, and anything not allowed denied rather than asked: the glossary,
	// the ADRs and the Inbox only, never a PRD. An Edit rule covers writing a file too.
	// The plugin is loaded from its folder too, since the session that ended may have had it
	// from somewhere the review's doesn't, such as --plugin-dir.
	cmd := exec.Command(claude, "-p", prompt, "--plugin-dir", plugin,
		"--tools", "Read,Glob,Grep,Edit,Write,Skill", "--permission-mode", "dontAsk",
		"--allowedTools", "Read", "Glob", "Grep", "Skill",
		"Edit(./.about/glossary.md)", "Edit(./"+names.ADRs+"**)", "Edit(./"+names.Inbox+")")
	cmd.Dir = root
	cmd.Env = append(os.Environ(), Env+"=1")
	cmd.Stdin, cmd.Stdout, cmd.Stderr = in, out, log
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true} // outlives Claude Code's exit
	if err := cmd.Start(); err != nil {
		os.Remove(reply)
		return false, err
	}
	os.WriteFile(pid, []byte(strconv.Itoa(cmd.Process.Pid)), 0o600)
	go cmd.Wait() // reaps it should this process outlive it, as a test's does
	return true, nil
}

// Last is what the last Session review at `root` changed, for Claude to tell the user, once: a
// line naming it, then up to `reported` lines of its reply; or that it is still running; nil when
// there was none, or it changed nothing it said.
func Last(root, data string) []string {
	reply, pid := files(root, data)
	text, err := os.ReadFile(reply)
	if err != nil {
		return nil
	}
	if id, err := os.ReadFile(pid); err == nil {
		if n, err := strconv.Atoi(string(id)); err == nil && running(n) {
			return []string{"the Session review of the last session is still running: tell the user, " +
				"since it may still change .about/"}
		}
	}
	os.Remove(reply)
	os.Remove(pid)
	started, rest, _ := strings.Cut(string(text), "\n")
	var lines []string
	for _, line := range strings.Split(rest, "\n") {
		if line = strings.TrimRight(line, " \t\r"); strings.TrimSpace(line) != "" {
			lines = append(lines, "  "+line)
		}
	}
	if len(lines) == 0 {
		return nil
	}
	if len(lines) > reported {
		lines = lines[len(lines)-reported:]
	}
	return append([]string{"the Session review of the last session (" + started + ") replied as " +
		"below: tell the user, and that what it changed is theirs to review and commit"}, lines...)
}

// running says whether the process `pid` still runs.
func running(pid int) bool {
	err := syscall.Kill(pid, 0)
	return pid > 0 && (err == nil || err == syscall.EPERM)
}
