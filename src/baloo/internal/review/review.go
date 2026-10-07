// Package review starts the Session review of a session that ended, which writes its Proposals to
// .about/proposals/<review>.md, and keeps what the user decides of each (ADR session-review).
package review

// cspell:ignore dont

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/condense"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Env is set in a Session review's environment, so that its own end starts no review.
var Env = strings.ToUpper(names.Plugin) + "_SESSION_REVIEW"

const (
	minChars = 2_000   // a shorter conversation can't have settled a term or a decision
	maxChars = 200_000 // of a longer one, the review reads the end
	kept     = 7 * 24 * time.Hour
)

// Headless says whether this process runs in a headless session, such as `claude -p` run by a
// project's own Git hook: Claude Code sets CLAUDE_CODE_ENTRYPOINT to sdk-cli there, sdk-ts or
// sdk-py from the Agent SDK, and cli or an editor's name in a session with the user. Nobody
// there can answer, so it is shown no Proposal.
func Headless() bool {
	return strings.HasPrefix(os.Getenv("CLAUDE_CODE_ENTRYPOINT"), "sdk-")
}

// prompt is what the review of `id` is asked: to write its Proposals to `file`.
func prompt(id, file string) string {
	return `The conversation that just ended is on stdin. Find what it settled or left open that
.about/ doesn't say yet, and propose each change to .about/ in ` + file + `; edit nothing else, and
never .about/ itself: the user accepts, rejects or defers each proposal later. Use the ` +
		names.Plugin + `:glossary and ` + names.Plugin + `:adr skills for what to check and for the
format of a term or an ADR, but write their result as a proposal. Nobody can answer questions:
propose only what the conversation clearly agreed, and only about this repo. Anything contested or
left open, and a bug or problem it found but didn't fix, is an Inbox item to add to ` +
		names.Inbox + `: a "## <title>", a line "<YYYY-MM-DD> · session review", then what it is and
what would settle it. An item the conversation settled is one to delete. A PRD changes only where
the conversation agreed what the feature is for or how it is checked.

Write nothing when there is nothing to propose. Otherwise write the file as:

# Session review ` + id + `

## P1 · <target> · <kind> · <path> · <title>

Why: <one line: what in the conversation it comes from>

Before:
~~~markdown
<the text it changes or deletes, copied exactly from the file>
~~~

After:
~~~markdown
<the text it adds, or the text that replaces Before>
~~~

Number them P1, P2… <target> is inbox, glossary, adr or prd, and <path> its file:
` + names.Inbox + `, ` + names.Glossary + `, ` + names.ADRs + `<subject>.md or ` + names.PRDs +
		`<feature>.md. <kind> is add (After only: the new text, a new file's whole text), edit
(Before and After) or delete (Before only). Keep each Before short but unique in its file. End your
reply with one line per proposal.`
}

// folder is where the reviews of the repo at `root` keep their files in the plugin's data folder
// `data`: per review, its reply, its process id while it runs and what it wrote to stderr.
func folder(root, data string) string {
	sum := sha256.Sum256([]byte(root))
	return filepath.Join(data, "session-review", hex.EncodeToString(sum[:8]))
}

// ID is the id of a review started at `at` of the session `session`: sorted by when it started.
func ID(at time.Time, session string) string {
	if len(session) > 8 {
		session = session[:8]
	}
	return at.UTC().Format("20060102T150405Z") + "-" + session
}

// Start starts the Session review of the session `session`, whose Transcript is `transcript`, with
// the `claude` given and the plugin in the folder `plugin`, whose skills it uses, at the repo's
// root `root`, keeping its files in the plugin's data folder `data`.
// It returns once the review runs, detached, and says whether one started: none does for a
// headless session, or one too short to have settled much.
func Start(claude, plugin, root, data, session string, transcript []byte) (bool, error) {
	if condense.Condense(transcript, "").Headless {
		return false, nil
	}
	conversation := condense.Conversation(transcript, maxChars)
	if len([]rune(conversation)) < minChars {
		return false, nil
	}
	dir := folder(root, data)
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return false, err
	}
	// The Proposals are the user's to decide, not to commit by accident with the rest.
	if err := settings.Exclude(root, filepath.Join(root, names.Proposals)); err != nil {
		return false, err
	}
	in, err := os.CreateTemp(dir, "conversation-*")
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
	id := ID(time.Now(), session)
	base := filepath.Join(dir, id)
	out, err := os.OpenFile(base+".txt", os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o600)
	if err != nil {
		return false, err
	}
	defer out.Close()
	errs, err := os.OpenFile(base+".err", os.O_WRONLY|os.O_CREATE|os.O_TRUNC, 0o600)
	if err != nil {
		return false, err
	}
	defer errs.Close()
	// Only reading, and writing its own Proposals; anything not allowed is denied rather than
	// asked. An Edit rule covers writing a file too.
	// The plugin is loaded from its folder too, since the session that ended may have had it
	// from somewhere the review's doesn't, such as --plugin-dir.
	file := "./" + names.Proposals + id + ".md"
	cmd := exec.Command(claude, "-p", prompt(id, file), "--plugin-dir", plugin,
		"--tools", "Read,Glob,Grep,Edit,Write,Skill", "--permission-mode", "dontAsk",
		"--allowedTools", "Read", "Glob", "Grep", "Skill", "Edit(./"+names.Proposals+"**)")
	cmd.Dir = root
	cmd.Env = append(os.Environ(), Env+"=1")
	cmd.Stdin, cmd.Stdout, cmd.Stderr = in, out, errs
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true} // outlives Claude Code's exit
	if err := cmd.Start(); err != nil {
		return false, err
	}
	os.WriteFile(base+".pid", []byte(strconv.Itoa(cmd.Process.Pid)), 0o600)
	go cmd.Wait() // reaps it should this process outlive it, as a test's does
	return true, nil
}

// Running says whether a Session review of the repo at `root` still runs. It also deletes the
// files of reviews that ended more than a week ago, and those Releases before reviews had ids
// kept, one per repo.
func Running(root, data string) bool {
	old, _ := filepath.Glob(filepath.Join(data, "session-review", "????????????????.txt*"))
	for _, f := range old {
		os.Remove(f)
	}
	pidFiles, _ := filepath.Glob(filepath.Join(folder(root, data), "*.pid"))
	running := false
	for _, pid := range pidFiles {
		id, err := os.ReadFile(pid)
		n, err2 := strconv.Atoi(strings.TrimSpace(string(id)))
		if err == nil && err2 == nil && alive(n) {
			running = true
			continue
		}
		if info, err := os.Stat(pid); err == nil && time.Since(info.ModTime()) > kept {
			base := strings.TrimSuffix(pid, ".pid")
			for _, ext := range []string{".pid", ".txt", ".err"} {
				os.Remove(base + ext)
			}
		}
	}
	return running
}

// alive says whether the process `pid` still runs.
func alive(pid int) bool {
	err := syscall.Kill(pid, 0)
	return pid > 0 && (err == nil || err == syscall.EPERM)
}
