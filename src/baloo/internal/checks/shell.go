package checks

import (
	"path"
	"regexp"
	"slices"
	"strings"
)

// program is one program a shell command runs: its name without its folder, its arguments, and
// the variables assigned for it (`HUSKY=0 git …`).
type program struct {
	name  string
	args  []string
	env   []string
	piped bool // its output goes into the next program, through a |
}

var assignment = regexp.MustCompile(`^[A-Za-z_]\w*=`)

// wrappers are programs that run the program after their own options and assignments; each
// maps to its options that take a value.
var wrappers = map[string][]string{
	"sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U"}, "doas": {"-u", "-C"},
	"env": {"-u", "-C", "-S"}, "command": nil, "exec": {"-a"}, "nohup": nil, "time": nil,
	"xargs": {"-I", "-L", "-n", "-P", "-s", "-d", "-E"},
}

var shells = []string{"sh", "bash", "zsh", "dash"}

// programs are the programs the shell command `command` runs, past wrappers such as sudo and env,
// and into `eval` and `sh -c`: enough to find each program and its arguments, not a full shell.
// An env with no program after it runs nothing but prints the environment, so it is one.
func programs(command string) []program {
	var found []program
	cmds, piped := segments(command)
	for i, words := range cmds {
		var env []string
		bareEnv := false
		for len(words) > 0 {
			if assignment.MatchString(words[0]) {
				env, words = append(env, words[0]), words[1:]
				continue
			}
			valued, ok := wrappers[path.Base(words[0])]
			if !ok {
				break
			}
			bareEnv = path.Base(words[0]) == "env"
			for words = words[1:]; len(words) > 0 && strings.HasPrefix(words[0], "-"); words = words[1:] {
				if slices.Contains(valued, words[0]) && len(words) > 1 {
					words = words[1:]
				}
			}
		}
		if len(words) == 0 {
			if bareEnv {
				found = append(found, program{"env", nil, env, piped[i]})
			}
			continue
		}
		name, args := path.Base(words[0]), words[1:]
		switch {
		case name == "eval":
			found = append(found, programs(strings.Join(args, " "))...)
		case slices.Contains(shells, name):
			script := func(a string) bool { return shortFlag(a, 'c') }
			if i := slices.IndexFunc(args, script); i >= 0 && i+1 < len(args) {
				found = append(found, programs(args[i+1])...)
			}
		default:
			found = append(found, program{name, args, env, piped[i]})
		}
	}
	return found
}

// split is the words of each simple command in `command`, split on ; & | ( ) ` and newlines,
// with quotes and backslashes taken off.
func split(command string) [][]string {
	cmds, _ := segments(command)
	return cmds
}

// segments is split's commands, each with whether a single | pipes its output into the next. A
// here-document's body is text a program reads, not commands, so it is left out, but for a shell's.
func segments(command string) (cmds [][]string, piped []bool) {
	cmds, piped = [][]string{nil}, []bool{false}
	var bodies []heredoc
	var word strings.Builder
	inWord := false
	flush := func() {
		if inWord {
			cmds[len(cmds)-1] = append(cmds[len(cmds)-1], word.String())
		}
		word.Reset()
		inWord = false
	}
	quote := rune(0)
	runes := []rune(command)
	for i := 0; i < len(runes); i++ {
		c := runes[i]
		switch {
		case quote != 0:
			switch {
			case c == quote:
				quote = 0
			case c == '\\' && quote == '"' && i+1 < len(runes):
				i++
				word.WriteRune(runes[i])
			default:
				word.WriteRune(c)
			}
		case c == '<' && i+1 < len(runes) && runes[i+1] == '<' &&
			(i+2 == len(runes) || runes[i+2] != '<') && (i == 0 || runes[i-1] != '<'):
			flush()
			var h heredoc
			h, i = heredocAt(runes, i+2)
			// A shell reads its here-document as commands: those are checked like any other.
			shell := func(w string) bool { return slices.Contains(shells, path.Base(w)) }
			if !slices.ContainsFunc(cmds[len(cmds)-1], shell) {
				bodies = append(bodies, h)
			}
		case c == '\n' && len(bodies) > 0:
			flush()
			cmds, piped = append(cmds, nil), append(piped, false)
			i = skipBodies(runes, i+1, bodies) - 1
			bodies = nil
		case c == '"' || c == '\'':
			quote, inWord = c, true
		case c == '\\' && i+1 < len(runes):
			i++
			if runes[i] != '\n' { // a backslash and a newline join two lines
				word.WriteRune(runes[i])
				inWord = true
			}
		case strings.ContainsRune(";&|()`\n", c):
			flush()
			piped[len(piped)-1] = c == '|' && (i+1 == len(runes) || runes[i+1] != '|') &&
				(i == 0 || runes[i-1] != '|')
			cmds, piped = append(cmds, nil), append(piped, false)
		case c == ' ' || c == '\t':
			flush()
		default:
			word.WriteRune(c)
			inWord = true
		}
	}
	flush()
	for i := len(cmds) - 1; i >= 0; i-- {
		if len(cmds[i]) == 0 {
			cmds, piped = slices.Delete(cmds, i, i+1), slices.Delete(piped, i, i+1)
		}
	}
	return cmds, piped
}

// heredoc is a here-document's delimiter, and whether its lines may start with tabs (<<-).
type heredoc struct {
	delim string
	tabs  bool
}

// heredocAt is the here-document whose << ends just before `at` in `runes`, and the index of the
// delimiter's last rune.
func heredocAt(runes []rune, at int) (heredoc, int) {
	var h heredoc
	if at < len(runes) && runes[at] == '-' {
		h.tabs, at = true, at+1
	}
	for at < len(runes) && (runes[at] == ' ' || runes[at] == '\t') {
		at++
	}
	var delim strings.Builder
	for ; at < len(runes) && !strings.ContainsRune(" \t\n;&|()<>", runes[at]); at++ {
		if !strings.ContainsRune(`'"\`, runes[at]) {
			delim.WriteRune(runes[at])
		}
	}
	h.delim = delim.String()
	return h, at - 1
}

// skipBodies is the index in `runes` just past the bodies of the here-documents `bodies`, which
// start at `at`, each ending at a line that is its delimiter.
func skipBodies(runes []rune, at int, bodies []heredoc) int {
	for _, h := range bodies {
		for at < len(runes) {
			end := at
			for end < len(runes) && runes[end] != '\n' {
				end++
			}
			line := string(runes[at:end])
			if h.tabs {
				line = strings.TrimLeft(line, "\t")
			}
			at = end + 1
			if line == h.delim {
				break
			}
		}
	}
	return min(at, len(runes))
}

// shortFlag says whether the argument `a` is the short flag -`f`, alone or among others (`-nm`).
func shortFlag(a string, f rune) bool {
	return len(a) > 1 && a[0] == '-' && a[1] != '-' && strings.ContainsRune(a[1:], f)
}

// gitValued are git's options before its subcommand that take the next argument as their value.
var gitValued = []string{"-C", "-c", "--git-dir", "--work-tree", "--namespace"}

// splitGit splits git's arguments `args` into the options before its subcommand, each followed
// by its value where it takes one, the subcommand, "" for none, and the subcommand's arguments.
func splitGit(args []string) (options []string, sub string, rest []string) {
	for len(args) > 0 && strings.HasPrefix(args[0], "-") {
		n := 1
		if slices.Contains(gitValued, args[0]) && len(args) > 1 {
			n = 2
		}
		options, args = append(options, args[:n]...), args[n:]
	}
	if len(args) == 0 {
		return options, "", nil
	}
	return options, args[0], args[1:]
}

// hasFlag says whether the arguments `args` have one of the flags `flags`: a long one as it is,
// a short one alone or among others (`-f` in `-fd`).
func hasFlag(args []string, flags ...string) bool {
	for _, f := range flags {
		for _, a := range args {
			if a == f || len(f) == 2 && f[0] == '-' && shortFlag(a, rune(f[1])) {
				return true
			}
		}
	}
	return false
}
