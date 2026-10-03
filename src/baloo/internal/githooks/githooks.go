// Package githooks writes the Git hooks that run the Checks the Config turns on, at session start
// (ADR git-hooks): into the folder git runs them from, or with husky 9 into the git folder, with a
// line in husky's own Git hook that runs each.
package githooks

import (
	"errors"
	"fmt"
	"io/fs"
	"maps"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/binlink"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/internal/settings"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Report is what Write did and what it left alone.
type Report struct {
	// Dir is the folder the plugin's Git hooks are in.
	Dir string
	// Written and Removed are the Git hooks it wrote where none of the plugin's was, and took out.
	Written, Removed []string
	// Husky are the files of husky's it changed, from the repo's root, for the user to commit.
	Husky []string
	// Theirs are the Git hooks it didn't write and left alone, which keep Checks that are on from
	// running.
	Theirs []Blocked
}

// Blocked is a Git hook of someone else's, at Path, and the Checks it keeps from running.
type Blocked struct {
	Path   string
	Checks []string
}

// Write brings the Git hooks of the repo at `root` in line with `on`, which says whether a Check is
// on: it writes each Git hook one of whose Checks is on, running the link in `data`, the plugin's
// data folder (see binlink), and takes out its own whose Checks are all off.
func Write(root, data string, on func(check string) bool) (Report, error) {
	dir, husky, err := locate(root)
	if err != nil {
		return Report{}, err
	}
	r := Report{Dir: dir}
	inTree := !husky && inside(root, r.Dir)
	bin := ""
	for _, hook := range slices.Sorted(maps.Keys(checks.GitHooks)) {
		running := runs(hook, on)
		path := filepath.Join(r.Dir, hook)
		current, err := os.ReadFile(path)
		had := err == nil
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			return r, err
		}
		if had && !ours(string(current)) {
			if len(running) > 0 {
				r.Theirs = append(r.Theirs, Blocked{path, running})
			}
			continue
		}
		if len(running) == 0 {
			if had {
				if err := os.Remove(path); err != nil {
					return r, err
				}
				r.Removed = append(r.Removed, hook)
			}
		} else {
			if bin == "" {
				if bin, err = binlink.Point(data); err != nil {
					return r, err
				}
			}
			if want := script(bin, hook); string(current) != want {
				if err := replace(path, want, 0o755); err != nil {
					return r, err
				}
				if !had {
					r.Written = append(r.Written, hook)
				}
			}
			if inTree {
				if err := settings.Exclude(root, path); err != nil {
					return r, err
				}
			}
		}
		if husky {
			changed, err := huskyRuns(filepath.Join(root, ".husky", hook), hook, len(running) > 0)
			if err != nil {
				return r, err
			}
			if changed {
				r.Husky = append(r.Husky, ".husky/"+hook)
			}
		}
	}
	return r, nil
}

// locate is the folder the plugin's Git hooks of the repo at `root` go in, and whether husky 9
// runs the repo's Git hooks, so the plugin's are in the git folder's instead (ADR git-hooks).
func locate(root string) (dir string, husky bool, err error) {
	out, err := exec.Command("git", "-C", root, "rev-parse", "--git-path", "hooks",
		"--git-common-dir").Output()
	if err != nil {
		return "", false, fmt.Errorf("git rev-parse: %w", err)
	}
	paths := strings.Split(strings.TrimSuffix(string(out), "\n"), "\n")
	if len(paths) != 2 {
		return "", false, fmt.Errorf("git rev-parse printed %q", out)
	}
	for i, p := range paths {
		if !filepath.IsAbs(p) {
			paths[i] = filepath.Join(root, p)
		}
	}
	hooks, common := paths[0], paths[1]
	if hooks == filepath.Join(root, ".husky", "_") && exists(filepath.Join(hooks, "h")) {
		return filepath.Join(common, names.Plugin+"-hooks"), true, nil
	}
	return hooks, false, nil
}

// runs are the Checks of the Git hook `hook` that `on` turns on, in the order it runs them.
func runs(hook string, on func(check string) bool) []string {
	var running []string
	for _, check := range checks.GitHooks[hook] {
		if on(check) {
			running = append(running, check)
		}
	}
	return running
}

// State is what Inspect finds of one of the plugin's Git hooks.
type State string

const (
	// Off: none of its Checks is on, and no Git hook of the plugin's is there.
	Off State = "off"
	// Running: the plugin's, as session start writes it, runs its Checks that are on.
	Running State = "running"
	// Missing: one of its Checks is on, but no Git hook is there.
	Missing State = "missing"
	// Theirs: a Git hook the plugin didn't write is there, and keeps its Checks that are on from
	// running.
	Theirs State = "theirs"
	// Outdated: the plugin's is there, but not as session start would write it now, such as one
	// running the link in another data folder.
	Outdated State = "outdated"
	// Leftover: the plugin's is there, but its Checks are all off.
	Leftover State = "leftover"
)

// Hook is one of the plugin's Git hooks as Inspect finds it.
type Hook struct {
	Name, Path string
	// Checks are its Checks the Config turns on.
	Checks []string
	State  State
	// Bin is the binary the plugin's Git hook runs, read from it; "" where none of the plugin's
	// is there.
	Bin string
	// HuskyOutdated says, with husky 9, that husky's own Git hook isn't as session start keeps
	// it: running the plugin's where Checks are on, and not where none is.
	HuskyOutdated bool
}

// Inspect finds the Git hooks of the repo at `root` as they are, against what Write would make of
// them with `on` and the link in `data`, the plugin's data folder, and changes nothing. It returns
// the folder they are in and whether husky 9 runs them.
func Inspect(root, data string, on func(check string) bool) (dir string, husky bool, hooks []Hook, err error) {
	dir, husky, err = locate(root)
	if err != nil {
		return "", false, nil, err
	}
	bin := filepath.Join(data, names.Plugin)
	for _, name := range slices.Sorted(maps.Keys(checks.GitHooks)) {
		h := Hook{Name: name, Path: filepath.Join(dir, name), Checks: runs(name, on)}
		text, err := os.ReadFile(h.Path)
		if err != nil && !errors.Is(err, fs.ErrNotExist) {
			return dir, husky, hooks, err
		}
		had := err == nil
		switch {
		case had && !ours(string(text)):
			h.State = Theirs
			if len(h.Checks) == 0 {
				h.State = Off
			}
		case !had && len(h.Checks) == 0:
			h.State = Off
		case !had:
			h.State = Missing
		case len(h.Checks) == 0:
			h.State = Leftover
		case data != "" && string(text) == script(bin, name):
			h.State = Running
		default:
			h.State = Outdated
		}
		if had && ours(string(text)) {
			h.Bin = runsBin(string(text))
		}
		if husky {
			text, _ := os.ReadFile(filepath.Join(root, ".husky", name))
			has := slices.Contains(strings.Split(string(text), "\n"), huskyLine(name))
			h.HuskyOutdated = has != (len(h.Checks) > 0)
		}
		hooks = append(hooks, h)
	}
	return dir, husky, hooks, nil
}

// runsBin is the binary the plugin's Git hook `text` runs, as script writes it, or "".
func runsBin(text string) string {
	for _, line := range strings.Split(text, "\n") {
		if q, ok := strings.CutPrefix(line, "b="); ok {
			return strings.ReplaceAll(strings.Trim(q, "'"), `'\''`, "'")
		}
	}
	return ""
}

// script is the Git hook `hook` that runs the binary at `bin`, marked as the plugin's on its second
// line.
func script(bin, hook string) string {
	return "#!/bin/sh\n" +
		names.Marker + ": runs the plugin's Checks, rewritten at each session start\n" +
		"b=" + quote(bin) + "\n" +
		`[ ! -x "$b" ] || exec "$b" git-hook ` + hook + ` "$@"` + "\n" +
		`echo "` + names.Plugin + `: $b is missing, so the plugin's Checks didn't run" >&2` + "\n"
}

// ours says whether the Git hook `text` is one the plugin wrote.
func ours(text string) bool {
	_, rest, _ := strings.Cut(text, "\n")
	return strings.HasPrefix(rest, names.Marker)
}

// huskyLine is the line in husky's Git hook `hook` that runs the plugin's, if it is there: the same
// in every clone, for it is committed.
func huskyLine(hook string) string {
	return `baloo_hook="$(git rev-parse --git-common-dir)/` + names.Plugin + `-hooks/` + hook + `"; ` +
		`[ ! -x "$baloo_hook" ] || "$baloo_hook" "$@" || exit $? ` + names.Marker
}

// huskyRuns puts the line that runs the plugin's Git hook `hook` first in husky's at `path`, after
// its #! line if it has one, creating the file when missing; or, not `run`, takes the line out,
// and the file with it when the line was all of it. It says whether it changed the file.
func huskyRuns(path, hook string, run bool) (bool, error) {
	data, err := os.ReadFile(path)
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return false, err
	}
	var kept []string
	for _, l := range strings.SplitAfter(string(data), "\n") {
		if l != "" && !strings.HasSuffix(strings.TrimRight(l, "\n"), names.Marker) {
			kept = append(kept, l)
		}
	}
	if run {
		at := 0
		if len(kept) > 0 && strings.HasPrefix(kept[0], "#!") {
			at = 1
		}
		kept = slices.Insert(kept, at, huskyLine(hook)+"\n")
	}
	text := strings.Join(kept, "")
	if text == string(data) {
		return false, nil
	}
	if strings.TrimSpace(text) == "" {
		return true, os.Remove(path)
	}
	mode := fs.FileMode(0o644)
	if info, err := os.Stat(path); err == nil {
		mode = info.Mode().Perm()
	}
	return true, replace(path, text, mode)
}

// replace writes `text` to the file at `path` with the mode `mode` in one step, so git never runs
// half a Git hook.
func replace(path, text string, mode fs.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + "." + strconv.Itoa(os.Getpid()) + ".tmp"
	err := os.WriteFile(tmp, []byte(text), mode)
	if err == nil {
		err = os.Chmod(tmp, mode)
	}
	if err == nil {
		err = os.Rename(tmp, path)
	}
	if err != nil {
		os.Remove(tmp)
	}
	return err
}

// quote is `s` quoted for sh.
func quote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

// inside says whether `path` is in the folder `dir`.
func inside(dir, path string) bool {
	rel, err := filepath.Rel(dir, path)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}
