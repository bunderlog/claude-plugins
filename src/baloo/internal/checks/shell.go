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
	name string
	args []string
	env  []string
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
func programs(command string) []program {
	var found []program
	for _, words := range split(command) {
		var env []string
		for len(words) > 0 {
			if assignment.MatchString(words[0]) {
				env, words = append(env, words[0]), words[1:]
				continue
			}
			valued, ok := wrappers[path.Base(words[0])]
			if !ok {
				break
			}
			for words = words[1:]; len(words) > 0 && strings.HasPrefix(words[0], "-"); words = words[1:] {
				if slices.Contains(valued, words[0]) && len(words) > 1 {
					words = words[1:]
				}
			}
		}
		if len(words) == 0 {
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
			found = append(found, program{name, args, env})
		}
	}
	return found
}

// split is the words of each simple command in `command`, split on ; & | ( ) ` and newlines,
// with quotes and backslashes taken off.
func split(command string) [][]string {
	cmds := [][]string{nil}
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
			cmds = append(cmds, nil)
		case c == ' ' || c == '\t':
			flush()
		default:
			word.WriteRune(c)
			inWord = true
		}
	}
	flush()
	return slices.DeleteFunc(cmds, func(c []string) bool { return len(c) == 0 })
}

// shortFlag says whether the argument `a` is the short flag -`f`, alone or among others (`-nm`).
func shortFlag(a string, f rune) bool {
	return len(a) > 1 && a[0] == '-' && a[1] != '-' && strings.ContainsRune(a[1:], f)
}
