package condense

import (
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"
)

// notLetterOrDigit is what Claude Code turns into `-` in the name of a project's folder of Transcripts.
var notLetterOrDigit = regexp.MustCompile(`[^A-Za-z0-9]`)

// Dir is the folder of the Transcripts of the project at `cwd`, or of the nearest folder above it
// that has one, in Claude Code's config folder `config`; "" when none has.
func Dir(config, cwd string) string {
	for dir := filepath.Clean(cwd); ; dir = filepath.Dir(dir) {
		path := filepath.Join(config, "projects", notLetterOrDigit.ReplaceAllString(dir, "-"))
		if info, err := os.Stat(path); err == nil && info.IsDir() {
			return path
		}
		if dir == filepath.Dir(dir) {
			return ""
		}
	}
}

// Read is the session of the Transcript file `path`, named after it.
func Read(path string) (Session, error) {
	text, err := os.ReadFile(path)
	if err != nil {
		return Session{}, err
	}
	return Condense(text, strings.TrimSuffix(filepath.Base(path), ".jsonl")), nil
}

// Latest are the `n` latest sessions in the folder `dir` worth a Retro, newest first: not
// headless, and something besides /clear was typed or failed.
func Latest(dir string, n int) ([]Session, error) {
	paths, err := filepath.Glob(filepath.Join(dir, "*.jsonl"))
	if err != nil {
		return nil, err
	}
	changed := map[string]time.Time{}
	for _, path := range paths {
		if info, err := os.Stat(path); err == nil {
			changed[path] = info.ModTime()
		}
	}
	slices.SortFunc(paths, func(a, b string) int { return changed[b].Compare(changed[a]) })
	var sessions []Session
	for _, path := range paths {
		if len(sessions) == n {
			break
		}
		s, err := Read(path)
		if err != nil {
			return nil, err
		}
		if s.worth() {
			sessions = append(sessions, s)
		}
	}
	return sessions, nil
}

var clear = regexp.MustCompile(`^/clear\b`)

// worth says whether the session is worth a Retro: not headless, and something besides /clear
// was typed or failed.
func (s Session) worth() bool {
	return !s.Headless && slices.ContainsFunc(s.Events, func(e Event) bool {
		return e.Type != "command" || !clear.MatchString(e.Text)
	})
}
