package guidelines

import (
	"bufio"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"
)

// byPath are the Guidelines that reach Claude by the file it works on, not by its own choice
// (ADR guidelines): each says whether a file, by its path from the repo's root, is one of its
// subject. Session start's index leaves them out.
var byPath = map[string]func(rel string) bool{
	"typescript": hasExt(".ts", ".tsx", ".mts", ".cts", ".vue"),
	"vue":        hasExt(".vue"),
	"testing":    isTest,
}

func hasExt(exts ...string) func(string) bool {
	return func(rel string) bool { return slices.Contains(exts, filepath.Ext(rel)) }
}

// isTest says whether the file at `rel` is a test: Go's, Python's, or a JavaScript or TypeScript
// one by its name or its __tests__ folder.
func isTest(rel string) bool {
	name := filepath.Base(rel)
	stem := strings.TrimSuffix(name, filepath.Ext(name))
	return strings.HasSuffix(name, "_test.go") ||
		strings.HasSuffix(name, ".py") && (strings.HasPrefix(name, "test_") || strings.HasSuffix(stem, "_test")) ||
		strings.HasSuffix(stem, ".test") || strings.HasSuffix(stem, ".spec") ||
		slices.Contains(strings.Split(filepath.ToSlash(filepath.Dir(rel)), "/"), "__tests__")
}

const kept = 7 * 24 * time.Hour

// ForFile is what Claude is to be told of the Guidelines `on` whose subject the file at `rel`,
// from the repo's root, is, and that the session `session` hasn't been given yet: each one's
// whole text, from the plugin at `plugin`. Each one given is marked for the session and logged in
// the plugin's data folder `data`, a line each: when, in UTC, the session, the Guideline and
// `rel`. It is "" where none is due.
func ForFile(plugin, data, session, rel string, on map[string]bool) (string, error) {
	var due []string
	for _, g := range All {
		if fits, ok := byPath[g.Name]; ok && on[g.Name] && fits(rel) {
			due = append(due, g.Name)
		}
	}
	if len(due) == 0 || data == "" { // without its data folder, it can't give each one only once
		return "", nil
	}
	dir := filepath.Join(data, "guidelines")
	shown := filepath.Join(dir, "shown")
	forget(shown)
	seen := filepath.Join(shown, session)
	given := lines(seen)
	var text []string
	var names []string
	for _, name := range due {
		if slices.Contains(given, name) {
			continue
		}
		body, err := os.ReadFile(path(plugin, name))
		if err != nil {
			return "", err
		}
		text = append(text, fmt.Sprintf("The %s Guideline applies to %s, which you just read or "+
			"changed; follow it for the rest of this session:\n\n%s", name, rel, strings.TrimSpace(string(body))))
		names = append(names, name)
	}
	if len(names) == 0 {
		return "", nil
	}
	if err := os.MkdirAll(shown, 0o700); err != nil {
		return "", err
	}
	if session != "" {
		if err := os.WriteFile(seen, []byte(strings.Join(append(given, names...), "\n")+"\n"), 0o600); err != nil {
			return "", err
		}
	}
	log, err := os.OpenFile(filepath.Join(dir, "guidelines.log"), os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0o600)
	if err != nil {
		return "", err
	}
	defer log.Close()
	at := time.Now().UTC().Format(time.RFC3339)
	for _, name := range names {
		fmt.Fprintf(log, "%s\t%s\t%s\t%s\n", at, session, name, filepath.ToSlash(rel))
	}
	return strings.Join(text, "\n\n"), nil
}

// lines are the lines of the file at `file`, none where it can't be read.
func lines(file string) []string {
	f, err := os.Open(file)
	if err != nil {
		return nil
	}
	defer f.Close()
	var got []string
	for s := bufio.NewScanner(f); s.Scan(); {
		if s.Text() != "" {
			got = append(got, s.Text())
		}
	}
	return got
}

// forget deletes what sessions were given more than a week ago.
func forget(dir string) {
	entries, err := os.ReadDir(dir)
	if errors.Is(err, fs.ErrNotExist) {
		return
	}
	for _, e := range entries {
		if info, err := e.Info(); err == nil && time.Since(info.ModTime()) > kept {
			os.Remove(filepath.Join(dir, e.Name()))
		}
	}
}
