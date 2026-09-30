// Package outputstyle picks one of the plugin's Output styles for a project, in the Claude Code
// settings file of the project that enables the plugin, where none of Claude Code's settings files
// picks one already (ADR output-styles).
package outputstyle

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

// Picked is an Output style Pick wrote: the file, and the Scope whose settings enable the plugin.
type Picked struct {
	Path    string
	Enabled Scope
}

// Pick sets outputStyle to the plugin's `style` for the project at `project`, in the repo at
// `root`, where the plugin is enabled in its local, project or user settings, and none of Claude
// Code's settings files sets outputStyle already, to any value. It writes the file that enables
// the plugin: the project's settings.json or settings.local.json, or for the user's settings the
// project's settings.local.json. It returns what it wrote, a zero Picked when it wrote nothing. A
// file it creates goes into the repo's info/exclude, as Claude Code does with its own.
func Pick(project, root, style string) (Picked, error) {
	paths := settings(project)
	fields := map[Scope]map[string]json.RawMessage{}
	for _, scope := range []Scope{Local, Project, User, Managed} {
		f, err := read(paths[scope])
		if err != nil {
			return Picked{}, err
		}
		if _, ok := f["outputStyle"]; ok {
			return Picked{}, nil
		}
		fields[scope] = f
	}
	enabled := enabling(fields)
	if enabled == "" {
		return Picked{}, nil
	}
	path := paths[Local]
	if enabled == Project {
		path = paths[Project]
	}
	data, err := os.ReadFile(path)
	created := errors.Is(err, fs.ErrNotExist)
	if err != nil && !created {
		return Picked{}, err
	}
	value, _ := json.Marshal(names.Plugin + ":" + style)
	data, err = with(data, `"outputStyle": `+string(value))
	if err != nil {
		return Picked{}, fmt.Errorf("%s: %v", path, err)
	}
	if err := replace(path, data); err != nil {
		return Picked{}, err
	}
	picked := Picked{path, enabled}
	if created {
		if err := exclude(root, path); err != nil {
			return picked, err
		}
	}
	return picked, nil
}

// settings are Claude Code's settings files for the project at `project`, by Scope; one Claude
// Code doesn't have is "".
func settings(project string) map[Scope]string {
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

// enabling is the Scope whose settings `fields` enable the plugin, or "" when none does: of the
// local, project and user settings, the most specific whose enabledPlugins names it decides, as
// in Claude Code. Managed settings don't count: a plugin they enable is the machine's, not a
// choice made for the project.
func enabling(fields map[Scope]map[string]json.RawMessage) Scope {
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

// with is the settings file `data` with `field` first in it, the rest of the file as it was; no
// data, or an object with nothing in it, is a new file.
func with(data []byte, field string) ([]byte, error) {
	var fields map[string]json.RawMessage
	if len(bytes.TrimSpace(data)) > 0 {
		if err := json.Unmarshal(data, &fields); err != nil {
			return nil, err
		}
	}
	if len(fields) == 0 {
		return []byte("{\n  " + field + "\n}\n"), nil
	}
	i := bytes.IndexByte(data, '{')
	out := append(append(data[:i+1:i+1], "\n  "+field+","...), data[i+1:]...)
	if !json.Valid(out) {
		return nil, errors.New("could not add outputStyle")
	}
	return out, nil
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

// exclude adds the file at `path` to the info/exclude of the repo at `root`, unless it is there.
func exclude(root, path string) error {
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
