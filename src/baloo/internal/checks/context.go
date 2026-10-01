package checks

// cspell:ignore netrc fgrep hexdump

import (
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
)

// ToolCall is what the Checks read of the tool call Claude Code gives a PreToolUse Hook: the
// tool, and the parts of its input that name a command, a file or what is written to one.
type ToolCall struct {
	Tool  string `json:"tool_name"`
	Input struct {
		Command   string `json:"command"`
		FilePath  string `json:"file_path"`
		Path      string `json:"path"`
		Glob      string `json:"glob"`
		Content   string `json:"content"`
		NewString string `json:"new_string"`
		Edits     []struct {
			NewString string `json:"new_string"`
		} `json:"edits"`
	} `json:"tool_input"`
}

var (
	keyFile = regexp.MustCompile(`(^|/)id_(rsa|dsa|ecdsa|ed25519)[^/]*$|\.(pem|key)$`)
	// secretPart is a part of a variable's name that says it holds a Secret: API_KEY,
	// GITHUB_TOKEN, DB_PASSWORD…
	secretPart = regexp.MustCompile(`^(\w*KEY|\w*TOKEN|\w*SECRET|PASSWORD|PASSWD|PASS|CREDENTIALS?|PAT)$`)
	variable   = regexp.MustCompile(`\$\{?([A-Za-z_]\w*)`)
	home       = regexp.MustCompile(`^(~|\$HOME|\$\{HOME\})(/|$)`)
)

// secretFiles are files that hold Secrets, by their path from the home folder or any other.
var secretFiles = []string{".aws/credentials", ".netrc", ".docker/config.json",
	".config/gh/hosts.yml"}

var (
	// readers are programs that show a file's contents.
	readers = []string{"cat", "bat", "less", "more", "head", "tail", "tac", "nl", "grep", "egrep",
		"fgrep", "rg", "ag", "sed", "awk", "cut", "sort", "uniq", "strings", "xxd", "od", "hexdump",
		"base64", "jq", "yq", "diff", "column", "view"}
	// patternFirst are readers whose first argument is a pattern or a script, not a file, unless
	// it is given with an option.
	patternFirst = []string{"grep", "egrep", "fgrep", "rg", "ag", "sed", "awk", "jq", "yq"}
)

// NoSecretsInContext is the Check baloo:no-secrets-in-context (PreToolUse on Bash, Read, Grep,
// Edit, Write and MultiEdit): why the tool call `call`, run in the folder `dir`, would Leak a
// Secret into Claude's context, or mark an Env file as holding none, which only the user does;
// "" when it would do neither. It says so to Claude, with what to ask the user instead.
func NoSecretsInContext(call ToolCall, dir string) string {
	in := call.Input
	written := []string{in.Content, in.NewString}
	for _, e := range in.Edits {
		written = append(written, e.NewString)
	}
	var why string
	switch call.Tool {
	case "Bash":
		if marks(in.Command) {
			return markAdvice
		}
		found := programs(in.Command)
		for i, p := range found {
			if why = shows(p, dir); why != "" && !(dumpsEnv(p) && keepsNames(found[i:])) {
				break
			}
			why = ""
		}
	case "Read":
		why = secretFile(in.FilePath, dir)
	case "Grep":
		if why = secretFile(in.Path, dir); why == "" {
			why = secretFile(in.Glob, dir)
		}
	case "Edit", "Write", "MultiEdit":
		if isEnvFile(in.FilePath) && slices.ContainsFunc(written, func(w string) bool {
			return strings.Contains(w, AllowSecret)
		}) {
			return markAdvice
		}
	}
	if why == "" {
		return ""
	}
	return why + ": showing it would put a secret into this session. If it's really needed, ask " +
		"the user to look in their own terminal, not with `!`, whose output enters the session."
}

const markAdvice = "only the user marks an env file as holding no secrets (" + AllowSecret +
	"). If it really holds none, ask the user to mark it themselves."

// marks says whether the shell command `command` would write AllowSecret into an Env file: it
// names both.
func marks(command string) bool {
	if !strings.Contains(command, AllowSecret) {
		return false
	}
	for _, words := range split(command) {
		for _, w := range words {
			if isEnvFile(strings.TrimLeft(w, "<>")) {
				return true
			}
		}
	}
	return false
}

// secretFile is why showing the file at `path`, from the folder `dir`, would Leak a Secret, or
// "" when it wouldn't. An Env file with AllowSecret on its first line holds none; one that can't
// be read counts as unmarked.
func secretFile(path, dir string) string {
	if path == "" {
		return ""
	}
	p := path
	if home.MatchString(p) {
		if h, err := os.UserHomeDir(); err == nil {
			p = home.ReplaceAllString(p, h+"$2")
		}
	}
	switch {
	case isEnvFile(p):
		if !filepath.IsAbs(p) {
			p = filepath.Join(dir, p)
		}
		text, err := os.ReadFile(p)
		first, _, _ := strings.Cut(string(text), "\n")
		if err == nil && strings.Contains(first, AllowSecret) {
			return ""
		}
		return path + " is an env file"
	case keyFile.MatchString(p) && !strings.HasSuffix(p, ".pub"):
		return path + " holds a private key"
	case slices.ContainsFunc(secretFiles, func(f string) bool {
		return p == f || strings.HasSuffix(p, "/"+f)
	}):
		return path + " holds secrets"
	}
	return ""
}

// shows is why the program `p`, run in `dir`, would show a Secret, or "" when it wouldn't: a
// file one of the readers shows, or redirected into any program (`… < .env`), or a Secret it
// prints itself.
func shows(p program, dir string) string {
	args := p.args
	pattern := -1
	withOption := hasFlag(args, "-e", "-f", "--regexp", "--file", "--expression")
	if slices.Contains(patternFirst, p.name) && !withOption {
		pattern = slices.IndexFunc(args, func(a string) bool { return !strings.HasPrefix(a, "-") })
	}
	for i, a := range args {
		file := ""
		switch {
		case strings.HasPrefix(a, "<"):
			if file = a[1:]; file == "" && i+1 < len(args) {
				file = args[i+1]
			}
		case slices.Contains(readers, p.name) && i != pattern:
			file = a
		}
		if why := secretFile(file, dir); why != "" {
			return why
		}
	}
	var named []string
	for _, a := range args {
		if !strings.HasPrefix(a, "-") {
			named = append(named, a)
		}
	}
	secret := func(names []string) string {
		if i := slices.IndexFunc(names, secretName); i >= 0 {
			return names[i]
		}
		return ""
	}
	switch p.name {
	case "env", "printenv":
		if dumpsEnv(p) {
			return p.name + " prints every environment variable"
		}
		if s := secret(named); p.name == "printenv" && s != "" {
			return "printenv " + s + " prints a secret"
		}
	case "export", "declare", "typeset":
		if len(named) == 0 {
			return p.name + " prints every exported variable"
		}
		if s := secret(named); hasFlag(args, "-p") && s != "" {
			return p.name + " -p " + s + " prints a secret"
		}
	case "set":
		if len(args) == 0 {
			return "set prints every shell variable"
		}
	case "echo", "printf", "print":
		var variables []string
		for _, a := range args {
			for _, m := range variable.FindAllStringSubmatch(a, -1) {
				variables = append(variables, m[1])
			}
		}
		if s := secret(variables); s != "" {
			return p.name + " $" + s + " prints a secret"
		}
	case "gh":
		if len(args) > 1 && args[0] == "auth" &&
			(args[1] == "token" || args[1] == "status" && hasFlag(args, "--show-token", "-t")) {
			return "gh auth token prints a secret"
		}
	case "security":
		if len(args) > 0 && (args[0] == "find-generic-password" || args[0] == "find-internet-password") &&
			hasFlag(args, "-w", "-g") {
			return "security " + args[0] + " -w prints a password"
		}
	case "aws":
		if len(args) > 1 && args[0] == "configure" && (args[1] == "export-credentials" ||
			args[1] == "get" && len(args) > 2 && secretName(args[2])) {
			return "aws configure " + args[1] + " prints a secret"
		}
	case "op":
		if len(args) > 0 && args[0] == "read" {
			return "op read prints a secret"
		}
	case "git":
		if _, sub, rest := splitGit(args); sub == "credential" && len(rest) > 0 && rest[0] == "fill" {
			return "git credential fill prints a secret"
		}
	}
	return ""
}

// dumpsEnv says whether the program `p` prints every environment variable: env or printenv
// without a name.
func dumpsEnv(p program) bool {
	return (p.name == "env" || p.name == "printenv") &&
		!slices.ContainsFunc(p.args, func(a string) bool { return !strings.HasPrefix(a, "-") })
}

// keepsNames says whether a later program of the pipeline that starts at `p[0]` keeps only the
// variables' names of what it is given, as `cut -d= -f1` does.
func keepsNames(p []program) bool {
	for i := 0; i+1 < len(p) && p[i].piped; i++ {
		if namesOnly(p[i+1]) {
			return true
		}
	}
	return false
}

// nameMatch is a grep -o pattern that can match only the start of a line, and no `=`.
var nameMatch = regexp.MustCompile(`^\^[\w()|\[\]*+?{},-]*$`)

// namesOnly says whether the program `p` prints only what comes before each line's first `=`.
func namesOnly(p program) bool {
	args := strings.Join(p.args, " ")
	switch p.name {
	case "cut":
		return regexp.MustCompile(`^-d ?= -f ?1$|^-f ?1 -d ?=$`).MatchString(args)
	case "awk":
		return regexp.MustCompile(`^-F ?= \{ ?print \$1 ?\}$`).MatchString(args)
	case "sed":
		script := strings.TrimSpace(strings.TrimPrefix(strings.TrimPrefix(args, "-E "), "-e "))
		if len(script) < 2 || script[0] != 's' {
			return false
		}
		parts := strings.Split(script[2:], script[1:2])
		return len(parts) == 3 && parts[0] == "=.*" && !strings.ContainsAny(parts[1], "&\\") &&
			(parts[2] == "" || parts[2] == "g")
	case "grep":
		var patterns []string
		for _, a := range p.args {
			if !strings.HasPrefix(a, "-") {
				patterns = append(patterns, a)
			}
		}
		return (hasFlag(p.args, "-o") || slices.Contains(p.args, "--only-matching")) &&
			len(patterns) == 1 && nameMatch.MatchString(patterns[0])
	}
	return false
}

// secretName says whether the variable's name `name` says it holds a Secret.
func secretName(name string) bool {
	return slices.ContainsFunc(strings.FieldsFunc(strings.ToUpper(name), func(r rune) bool {
		return r == '_' || r == '.' || r == '-'
	}), secretPart.MatchString)
}
