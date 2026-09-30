package checks

// cspell:ignore AKIA pousr abprs bxox ACMR

import (
	"bytes"
	"fmt"
	"os/exec"
	"regexp"
	"strconv"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// AllowSecret marks a false alarm of NoSecretsInCommits: on a line, or on an Env file's first line.
const AllowSecret = names.Plugin + ":allow-secret"

// secretKinds name each kind of Secret; the first that matches names it, so the more specific
// come first.
var secretKinds = []struct {
	what string
	re   *regexp.Regexp
}{
	{"a private key", regexp.MustCompile(`-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----`)},
	{"an AWS access key", regexp.MustCompile(`\b(?:AKIA|ASIA)[0-9A-Z]{16}\b`)},
	{"a GitHub token", regexp.MustCompile(`\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})`)},
	{"a Slack token", regexp.MustCompile(`\bxox[abprs]-[A-Za-z0-9-]{10,}`)},
	{"a Stripe live key", regexp.MustCompile(`\b[rs]k_live_[A-Za-z0-9]{20,}`)},
	{"an Anthropic API key", regexp.MustCompile(`\bsk-ant-[A-Za-z0-9_-]{20,}`)},
	{"an OpenAI API key", regexp.MustCompile(`\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}`)},
	{"a Google API key", regexp.MustCompile(`\bAIza[0-9A-Za-z_-]{35}`)},
}

var (
	// envFile is an Env file: .env, .env.local, prod.env, .envrc…
	envFile = regexp.MustCompile(`(^|/)(\.env(\.[^/]*)?|\.envrc|[^/]*\.env)$`)
	// template is an Env file's template, meant to be committed.
	template = regexp.MustCompile(`\.(example|sample|template|dist)$`)
	hunk     = regexp.MustCompile(`^@@ -\d+(?:,\d+)? \+(\d+)`)
)

// staged is the git diff of the staged files added, copied, changed or renamed, as git itself
// prints it, whatever the repo's config says of diffs.
var staged = []string{"diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color",
	"--diff-filter=ACMR"}

// NoSecretsInCommits is the Check baloo:no-secrets-in-commits (pre-commit): the Leaks the staged
// changes of the repo `dir` would commit, each as `<path>: an env file…` or `<path>:<line>:
// <what>`, never the Secret itself. A line with AllowSecret on it passes, and an Env file with it
// on its first line, whose lines are still looked through. It errs where git does, such as
// outside a repo.
func NoSecretsInCommits(dir string) ([]string, error) {
	list, err := git(dir, append(staged, "--name-only", "-z")...)
	if err != nil {
		return nil, err
	}
	var found []string
	for _, path := range strings.Split(strings.TrimSuffix(list, "\x00"), "\x00") {
		if !isEnvFile(path) {
			continue
		}
		text, err := git(dir, "cat-file", "blob", ":"+path)
		if err != nil {
			return nil, err
		}
		if first, _, _ := strings.Cut(text, "\n"); !strings.Contains(first, AllowSecret) {
			found = append(found, path+": an env file; keep it out of git, or put "+AllowSecret+
				" on its first line")
		}
	}
	diff, err := git(dir, append(staged, "--no-prefix", "-U0")...)
	if err != nil {
		return nil, err
	}
	return append(found, scan(diff)...), nil
}

// isEnvFile says whether the file at `path` is an Env file, not a template of one.
func isEnvFile(path string) bool {
	return envFile.MatchString(path) && !template.MatchString(path)
}

// scan is `<path>:<line>: <what>` for each Secret on a line the diff `diff` adds.
func scan(diff string) []string {
	var found []string
	var path string
	line, header := 0, false
	for _, text := range strings.Split(diff, "\n") {
		switch {
		case strings.HasPrefix(text, "diff --git "):
			header = true
		case header && strings.HasPrefix(text, "+++ "):
			path = text[len("+++ "):]
		case strings.HasPrefix(text, "@@"):
			header = false
			if m := hunk.FindStringSubmatch(text); m != nil {
				line, _ = strconv.Atoi(m[1])
			}
		case !header && strings.HasPrefix(text, "+"):
			if !strings.Contains(text, AllowSecret) {
				for _, kind := range secretKinds {
					if kind.re.MatchString(text) {
						found = append(found, fmt.Sprintf("%s:%d: %s", path, line, kind.what))
						break
					}
				}
			}
			line++
		}
	}
	return found
}

// git runs git in `dir` with `args`, and returns what it prints, or why it failed.
func git(dir string, args ...string) (string, error) {
	var stderr bytes.Buffer
	cmd := exec.Command("git", append([]string{"-C", dir}, args...)...)
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("git %s: %v: %s", args[0], err, strings.TrimSpace(stderr.String()))
	}
	return string(out), nil
}
