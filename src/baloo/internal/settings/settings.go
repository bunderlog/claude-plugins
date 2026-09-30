// Package settings reads Claude Code's settings files for a project and writes one of their
// top-level fields, the rest of the file's text as it was, for what session start sets in them
// (ADR output-styles, ADR status-line).
package settings

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// managed is Claude Code's managed settings file on this machine; a test points it elsewhere
// with BALOO_MANAGED_SETTINGS.
func managed() string {
	if path := os.Getenv("BALOO_MANAGED_SETTINGS"); path != "" {
		return path
	}
	return map[string]string{
		"darwin": "/Library/Application Support/ClaudeCode/managed-settings.json",
		"linux":  "/etc/claude-code/managed-settings.json",
	}[runtime.GOOS]
}

// Scope is one of Claude Code's settings files for a project, by whom it is for.
type Scope string

const (
	Local   Scope = "local"   // the project's .claude/settings.local.json, one person's
	Project Scope = "project" // the project's .claude/settings.json, its team's
	User    Scope = "user"    // the user's own settings.json, for every project
	Managed Scope = "managed" // the machine's managed settings
)

// Scopes are the Scopes from the most specific to the least, managed last, since it wins over
// all of them.
var Scopes = []Scope{Local, Project, User, Managed}

// Files are Claude Code's settings files for the project at `project`, by Scope; one Claude Code
// doesn't have is "".
func Files(project string) map[Scope]string {
	own := os.Getenv("CLAUDE_CONFIG_DIR")
	if home, err := os.UserHomeDir(); own == "" && err == nil {
		own = filepath.Join(home, ".claude")
	}
	user := ""
	if own != "" {
		user = filepath.Join(own, "settings.json")
	}
	return map[Scope]string{
		Local:   filepath.Join(project, names.LocalSettings),
		Project: filepath.Join(project, names.ProjectSettings),
		User:    user,
		Managed: managed(),
	}
}

// ReadAll is every settings file in `files`, its top-level fields, by Scope.
func ReadAll(files map[Scope]string) (map[Scope]map[string]json.RawMessage, error) {
	fields := map[Scope]map[string]json.RawMessage{}
	for _, scope := range Scopes {
		f, err := read(files[scope])
		if err != nil {
			return nil, err
		}
		fields[scope] = f
	}
	return fields, nil
}

// read is the settings file at `path`, its top-level fields; one that isn't there, or is empty,
// has none.
func read(path string) (map[string]json.RawMessage, error) {
	if path == "" {
		return nil, nil
	}
	data, err := os.ReadFile(path)
	if errors.Is(err, fs.ErrNotExist) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if len(bytes.TrimSpace(data)) == 0 {
		return nil, nil
	}
	var fields map[string]json.RawMessage
	if err := json.Unmarshal(data, &fields); err != nil {
		return nil, fmt.Errorf("%s: %v", path, err)
	}
	return fields, nil
}

// Enabling is the Scope whose settings `fields` enable the plugin, or "" when none does: of the
// local, project and user settings, the most specific whose enabledPlugins names it decides, as
// in Claude Code. Managed settings don't count: a plugin they enable is the machine's, not a
// choice made for the project.
func Enabling(fields map[Scope]map[string]json.RawMessage) Scope {
	for _, scope := range []Scope{Local, Project, User} {
		var plugins map[string]json.RawMessage
		if json.Unmarshal(fields[scope]["enabledPlugins"], &plugins) != nil {
			continue
		}
		if value, ok := plugins[names.PluginID]; ok {
			var on bool
			if json.Unmarshal(value, &on) == nil && on {
				return scope
			}
			return ""
		}
	}
	return ""
}

// Set sets the top-level field `key` of the settings file at `path` to `value`, the rest of the
// file's text as it was, and says whether it created the file, which then goes into the repo's
// info/exclude (see Exclude).
func Set(path, key string, value any) (created bool, err error) {
	data, err := os.ReadFile(path)
	created = errors.Is(err, fs.ErrNotExist)
	if err != nil && !created {
		return false, err
	}
	v, err := json.Marshal(value)
	if err != nil {
		return false, err
	}
	if data, err = set(data, key, v); err != nil {
		return false, fmt.Errorf("%s: %v", path, err)
	}
	return created, replace(path, data)
}

// Delete takes the top-level field `key` out of the settings file at `path`, the rest of the
// file's text as it was; a file without it is left alone.
func Delete(path, key string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	member, _, ok, err := find(data, key)
	if err != nil || !ok {
		return err
	}
	out := append(data[:member[0]:member[0]], data[member[1]:]...)
	if !json.Valid(out) {
		return fmt.Errorf("%s: could not take out %s", path, key)
	}
	return replace(path, out)
}

// set is the settings file `data` with its top-level field `key` set to the JSON `value`: in
// place where it has the field, else first in it, the rest of the file as it was; no data, or an
// object with nothing in it, is a new file.
func set(data []byte, key string, value []byte) ([]byte, error) {
	name, _ := json.Marshal(key)
	field := string(name) + ": " + string(value)
	var fields map[string]json.RawMessage
	if len(bytes.TrimSpace(data)) > 0 {
		if err := json.Unmarshal(data, &fields); err != nil {
			return nil, err
		}
	}
	if len(fields) == 0 {
		return []byte("{\n  " + field + "\n}\n"), nil
	}
	_, old, ok, err := find(data, key)
	if err != nil {
		return nil, err
	}
	var out []byte
	if ok {
		out = append(append(data[:old[0]:old[0]], value...), data[old[1]:]...)
	} else {
		i := bytes.IndexByte(data, '{')
		out = append(append(data[:i+1:i+1], "\n  "+field+","...), data[i+1:]...)
	}
	if !json.Valid(out) {
		return nil, errors.New("could not set " + key)
	}
	return out, nil
}

// find is where the top-level field `key` is in the JSON object `data`, as byte offsets: the
// field whole, with the comma that parts it from the one before, or for the first field from the
// one after, and its value alone; ok is false when the object has no such field.
func find(data []byte, key string) (member, value [2]int, ok bool, err error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	if t, err := dec.Token(); err != nil || t != json.Delim('{') {
		return member, value, false, errors.New("not a JSON object")
	}
	for i := 0; dec.More(); i++ {
		start := int(dec.InputOffset())
		name, err := dec.Token()
		if err != nil {
			return member, value, false, err
		}
		var raw json.RawMessage
		if err := dec.Decode(&raw); err != nil {
			return member, value, false, err
		}
		end := int(dec.InputOffset())
		if name != key {
			continue
		}
		value = [2]int{end - len(raw), end}
		member = [2]int{start, end}
		if i == 0 {
			// The first field goes with the comma after it and the space up to the next one, and
			// the only one with the space before it.
			rest := bytes.TrimLeft(data[end:], " \t\r\n")
			if after, ok := bytes.CutPrefix(rest, []byte(",")); ok {
				member[1] = len(data) - len(bytes.TrimLeft(after, " \t\r\n"))
			} else {
				member[0] = bytes.IndexByte(data, '{') + 1
			}
		}
		return member, value, true, nil
	}
	return member, value, false, nil
}

// replace writes `data` to the file at `path` whole or not at all: to a new file beside it, then
// renamed over it, so a write cut short, or one of Claude Code's own at the same moment, never
// leaves half a settings file. A link is followed, and the file keeps its mode.
func replace(path string, data []byte) error {
	if real, err := filepath.EvalSymlinks(path); err == nil {
		path = real
	}
	mode := fs.FileMode(0o644)
	if info, err := os.Stat(path); err == nil {
		mode = info.Mode().Perm()
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	f, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".*")
	if err != nil {
		return err
	}
	_, err = f.Write(data)
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err == nil {
		err = os.Chmod(f.Name(), mode)
	}
	if err == nil {
		err = os.Rename(f.Name(), path)
	}
	if err != nil {
		os.Remove(f.Name())
	}
	return err
}

// Exclude adds the file at `path` to the info/exclude of the repo at `root`, unless it is there,
// as Claude Code does with a settings.local.json it creates.
func Exclude(root, path string) error {
	rel, err := filepath.Rel(root, path)
	if err != nil {
		return err
	}
	dir, err := gitDir(root)
	if err != nil {
		return err
	}
	line := "/" + pattern(filepath.ToSlash(rel))
	file := filepath.Join(dir, "info", "exclude")
	data, err := os.ReadFile(file)
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return err
	}
	for _, l := range strings.Split(string(data), "\n") {
		if strings.TrimSpace(l) == line {
			return nil
		}
	}
	if len(data) > 0 && !bytes.HasSuffix(data, []byte("\n")) {
		line = "\n" + line
	}
	if err := os.MkdirAll(filepath.Dir(file), 0o755); err != nil {
		return err
	}
	f, err := os.OpenFile(file, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0o644)
	if err != nil {
		return err
	}
	_, err = f.WriteString(line + "\n")
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	return err
}

// pattern is the gitignore pattern that matches the path `rel` and nothing else: its wildcards
// and backslashes escaped, and a trailing space kept.
func pattern(rel string) string {
	var b strings.Builder
	for _, r := range rel {
		if strings.ContainsRune(`\*?[`, r) {
			b.WriteByte('\\')
		}
		b.WriteRune(r)
	}
	p := b.String()
	if trimmed := strings.TrimRight(p, " "); trimmed != p {
		p = trimmed + strings.Repeat(`\ `, len(p)-len(trimmed))
	}
	return p
}

// gitDir is the folder holding the info/ of the repo at `root`: its .git folder, or for a
// worktree, whose .git is a file naming its own folder, the folder its worktrees share.
func gitDir(root string) (string, error) {
	dir := filepath.Join(root, ".git")
	info, err := os.Stat(dir)
	if err != nil || info.IsDir() {
		return dir, err
	}
	data, err := os.ReadFile(dir)
	if err != nil {
		return "", err
	}
	named, ok := strings.CutPrefix(strings.TrimSpace(string(data)), "gitdir: ")
	if !ok {
		return "", fmt.Errorf("%s names no gitdir", dir)
	}
	if !filepath.IsAbs(named) {
		named = filepath.Join(root, named)
	}
	common, err := os.ReadFile(filepath.Join(named, "commondir"))
	if errors.Is(err, fs.ErrNotExist) {
		return named, nil
	}
	if err != nil {
		return "", err
	}
	shared := strings.TrimSpace(string(common))
	if !filepath.IsAbs(shared) {
		shared = filepath.Join(named, shared)
	}
	return shared, nil
}
