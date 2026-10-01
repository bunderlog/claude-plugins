package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Commit is one commit since the last Release: its short sha and full message.
type Commit struct{ SHA, Message string }

// Changes are the paths whose change needs a Release, and whose commits alone count for its version
// and CHANGELOG: the plugin and its binary's source, but not what users don't get from a Release:
// tests, and the schema, which editors read from main.
var Changes = []string{
	names.PluginDir, names.Src, ":!*_test.go", ":!" + names.PluginDir + "/schema.json",
}

const changelogHeader = "# Changelog\n\nThe " + names.Plugin + " plugin's Releases, newest first.\n"

// A Conventional Commits subject: type, optional scope, optional `!`, description.
var subject = regexp.MustCompile(`^(\w+)(?:\(([^)]*)\))?(!)?: (.+)$`)

var breakingFooter = regexp.MustCompile(`(?m)^BREAKING[ -]CHANGE: `)

func parts(c Commit) []string {
	first, body, _ := strings.Cut(c.Message, "\n")
	m := subject.FindStringSubmatch(first)
	if m == nil {
		m = make([]string, 5)
	}
	if breakingFooter.MatchString(body) {
		m[3] = "!"
	}
	return m
}

func breaking(c Commit) bool  { return parts(c)[3] == "!" }
func kind(c Commit) string    { return parts(c)[1] }
func isFeature(c Commit) bool { return !breaking(c) && kind(c) == "feat" }
func isFix(c Commit) bool     { return !breaking(c) && kind(c) == "fix" }
func filter(cs []Commit, keep func(Commit) bool) (out []Commit) {
	for _, c := range cs {
		if keep(c) {
			out = append(out, c)
		}
	}
	return out
}

// Next is the version after `version` for these commits, or "" when the plugin didn't change.
// Below 1.0 a breaking change raises the minor, as a feat does; from 1.0 it raises the major;
// anything else raises the patch.
func Next(version string, commits []Commit, changed bool) (string, error) {
	if !changed {
		return "", nil
	}
	var v [3]int
	fields := strings.Split(version, ".")
	if len(fields) != 3 {
		return "", fmt.Errorf("version %q is not major.minor.patch", version)
	}
	for i, f := range fields {
		n, err := strconv.Atoi(f)
		if err != nil {
			return "", fmt.Errorf("version %q is not major.minor.patch", version)
		}
		v[i] = n
	}
	switch {
	case len(filter(commits, breaking)) > 0 && v[0] > 0:
		v = [3]int{v[0] + 1, 0, 0}
	case len(filter(commits, breaking)) > 0, len(filter(commits, isFeature)) > 0:
		v = [3]int{v[0], v[1] + 1, 0}
	default:
		v[2]++
	}
	return fmt.Sprintf("%d.%d.%d", v[0], v[1], v[2]), nil
}

// Section is the CHANGELOG section for `version`: its breaking changes, features and fixes,
// oldest first.
func Section(version, date string, commits []Commit) string {
	var body strings.Builder
	for _, group := range []struct {
		title string
		keep  func(Commit) bool
	}{{"Breaking changes", breaking}, {"Features", isFeature}, {"Fixes", isFix}} {
		list := filter(commits, group.keep)
		if len(list) == 0 {
			continue
		}
		if body.Len() > 0 {
			body.WriteString("\n")
		}
		fmt.Fprintf(&body, "### %s\n\n", group.title)
		for _, c := range list {
			m := parts(c)
			scope := ""
			if m[2] != "" {
				scope = m[2] + ": "
			}
			fmt.Fprintf(&body, "- %s%s (%s)\n", scope, m[4], c.SHA)
		}
	}
	if body.Len() == 0 {
		body.WriteString("No feature changes or fixes.\n")
	}
	return fmt.Sprintf("## %s — %s\n\n%s", version, date, body.String())
}

// pinned is the line of the README's CI recipe that names the Release it pins.
var pinned = regexp.MustCompile(`(?m)^version=\S+$`)

// Pin is the README `readme` with its CI recipe pinning `version`; an error unless it has exactly
// one line to pin.
func Pin(readme []byte, version string) ([]byte, error) {
	if n := len(pinned.FindAll(readme, -1)); n != 1 {
		return nil, fmt.Errorf("README.md has %d lines `version=<version>` for its CI recipe; want one", n)
	}
	return pinned.ReplaceAll(readme, []byte("version="+version)), nil
}

func git(root string, args ...string) (string, error) {
	out, err := exec.Command("git", append([]string{"-C", root}, args...)...).Output()
	return strings.TrimSpace(string(out)), err
}

// Release makes a Release in the repo at `root` from the commits since the last `v*` tag: it
// builds the next version for every platform, to check that it builds, writes it to the manifest
// and the README's CI recipe and a section to CHANGELOG.md, commits these and tags the commit,
// whose push has CI build and publish the binaries. It returns the version.
func Release(root, date string) (string, error) {
	if status, err := git(root, "status", "--porcelain"); err != nil || status != "" {
		return "", fmt.Errorf("commit or stash your changes first")
	}
	current, err := Version(root)
	if err != nil {
		return "", err
	}
	since := "HEAD"
	changed := true
	if tag, err := git(root, "describe", "--tags", "--abbrev=0", "--match", "v*"); err == nil {
		if tag[1:] != current {
			return "", fmt.Errorf("the last tag is %s, but %s says %s", tag, names.Manifest, current)
		}
		since = tag + "..HEAD"
		diff, err := git(root, append([]string{"diff", "--name-only", tag, "HEAD", "--"}, Changes...)...)
		if err != nil {
			return "", err
		}
		changed = diff != ""
	}
	log, err := git(root, append([]string{"log", "--reverse", "--format=%h%x00%B%x1e", since, "--"},
		Changes...)...)
	if err != nil {
		return "", err
	}
	var commits []Commit
	for _, entry := range strings.Split(log, "\x1e") {
		sha, message, _ := strings.Cut(strings.TrimSpace(entry), "\x00")
		if sha != "" {
			commits = append(commits, Commit{sha, strings.TrimSpace(message)})
		}
	}
	version, err := Next(current, commits, changed)
	if err != nil {
		return "", err
	}
	if version == "" {
		return "", fmt.Errorf("nothing to release: %s is unchanged since v%s", strings.Join(Changes, " "), current)
	}
	// A version that doesn't build is never tagged: CI would publish no GitHub Release for it, and
	// every Loader would fail to download it.
	built, err := os.MkdirTemp("", "release")
	if err != nil {
		return "", err
	}
	defer os.RemoveAll(built)
	if _, err := Build(root, built, version); err != nil {
		return "", err
	}

	// Every file is read and checked before any is written, so a failure leaves none half done.
	readme := filepath.Join(root, "README.md")
	text, err := os.ReadFile(readme)
	if err != nil {
		return "", err
	}
	pinnedReadme, err := Pin(text, version)
	if err != nil {
		return "", err
	}
	manifest := filepath.Join(root, names.Manifest)
	text, err = os.ReadFile(manifest)
	if err != nil {
		return "", err
	}
	bumped := regexp.MustCompile(`("version":\s*")[^"]*"`).ReplaceAll(text, []byte(`${1}`+version+`"`))
	file := filepath.Join(root, "CHANGELOG.md")
	old, err := os.ReadFile(file)
	if os.IsNotExist(err) {
		old, err = []byte(changelogHeader), nil
	}
	if err != nil {
		return "", err
	}
	entry := "\n" + Section(version, date, commits)
	changelog := string(old) + entry
	if at := strings.Index(string(old), "\n## "); at >= 0 {
		changelog = string(old[:at]) + entry + string(old[at:])
	}
	for path, text := range map[string][]byte{manifest: bumped, file: []byte(changelog), readme: pinnedReadme} {
		if err := os.WriteFile(path, text, 0o644); err != nil {
			return "", err
		}
	}

	if _, err := git(root, "add", names.Manifest, "CHANGELOG.md", "README.md"); err != nil {
		return "", err
	}
	msg := "chore(release): " + version
	commit := exec.Command("git", "-C", root, "commit", "-q", "-m", msg)
	commit.Stdout, commit.Stderr = os.Stderr, os.Stderr
	if err := commit.Run(); err != nil {
		return "", fmt.Errorf("the release commit failed: fix what failed, then "+
			"`git commit -m %q && git tag -s v%s -m v%s`", msg, version, version)
	}
	// Signed whatever tag.gpgSign says, as ADR releases has it: -a alone would make an unsigned
	// tag.
	if out, err := exec.Command("git", "-C", root, "tag", "-s", "v"+version, "-m", "v"+version).CombinedOutput(); err != nil {
		return "", fmt.Errorf("the release tag failed: fix what failed, then `git tag -s v%s -m v%s`: %s",
			version, version, out)
	}
	return version, nil
}
