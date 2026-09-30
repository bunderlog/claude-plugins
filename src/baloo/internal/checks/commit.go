package checks

import (
	"fmt"
	"regexp"
	"slices"
	"strings"
	"unicode"
	"unicode/utf8"
)

var (
	subject = regexp.MustCompile(`^[\p{L}\p{N}][\p{L}\p{N}-]*(\([^()\n]*[^()\s][^()\n]*\))?!?: \S`)
	header  = regexp.MustCompile(`^([^(!:]*)(?:\([^()]*\))?!?: (.*)$`)
	quoted  = regexp.MustCompile("`[^`]*`|\"[^\"]*\"|'[^']*'")
	letter  = regexp.MustCompile(`^[a-zA-Z]`)
	// footer is a footer's word token (`-` for spaces; BREAKING CHANGE the one exception) and
	// its separator.
	footer   = regexp.MustCompile(`^([\p{L}\p{N}-]+|BREAKING CHANGE)(: | #)`)
	breaking = regexp.MustCompile(`(?i)^breaking[ -]change$`)
	// byGit is a message git, or a pull request's merge, writes itself.
	byGit = regexp.MustCompile(`^Merge (branch|branches|remote-tracking branch|tag|commit|pull request) |` +
		`^(Revert|Reapply) "|^(fixup|squash|amend)! `)
	newline   = regexp.MustCompile(`\r?\n`)
	paragraph = regexp.MustCompile(`\n\s*\n`)
)

// commitTypes are config-conventional's types.
var commitTypes = []string{"build", "chore", "ci", "docs", "feat", "fix", "perf", "refactor",
	"revert", "style", "test"}

// maxLine is the longest line a commit message may have, in characters.
const maxLine = 100

// ConventionalCommit is the Check baloo:conventional-commits (commit-msg): why the commit message
// isn't a Conventional Commit as commitlint's config-conventional reads it (its error rules), or
// "" when it is. That is a `type(scope)!: description` subject with one of its types, a
// description not starting in uppercase (quoted text aside) nor ending in `.`, a trimmed header,
// a body after a blank line, lines of up to 100 characters, and a breaking change footer as
// `BREAKING CHANGE: description`, in uppercase (its synonym `BREAKING-CHANGE` too). Footers are
// the trailing paragraphs that open with one. A message git writes itself, such as a merge's,
// passes.
func ConventionalCommit(message string) string {
	var lines []string
	for _, l := range newline.Split(scissors.Split(message, 2)[0], -1) {
		if !strings.HasPrefix(l, "#") {
			lines = append(lines, l)
		}
	}
	start := slices.IndexFunc(lines, func(l string) bool { return strings.TrimSpace(l) != "" })
	if start < 0 || byGit.MatchString(lines[start]) {
		return ""
	}
	lines = lines[start:]
	s := lines[0]
	if !subject.MatchString(s) {
		return `"` + s + `" is not ` + "`type(scope): description`"
	}
	m := header.FindStringSubmatch(s)
	kind, description := m[1], m[2]
	if !slices.Contains(commitTypes, kind) {
		return `"` + kind + `" is not one of ` + strings.Join(commitTypes, ", ")
	}
	// Quoted text, such as `README`, may be in uppercase; a description that opens with it too.
	first, _ := utf8.DecodeRuneInString(strings.TrimSpace(quoted.ReplaceAllString(description, "")))
	if letter.MatchString(description) && unicode.IsUpper(first) {
		return `"` + description + `" starts with an uppercase letter`
	}
	if strings.HasSuffix(description, ".") {
		return `"` + description + `" ends with a full stop`
	}
	if s != strings.TrimSpace(s) {
		return `"` + s + `" has trailing spaces`
	}
	if len(lines) > 1 && strings.TrimSpace(lines[1]) != "" {
		return `leave a blank line between "` + s + `" and the body`
	}
	for _, l := range lines {
		if n := utf8.RuneCountInString(l); n > maxLine {
			return fmt.Sprintf(`"%s…" is %d characters, over %d`, string([]rune(l)[:40]), n, maxLine)
		}
	}
	paragraphs := paragraph.Split(strings.TrimSpace(strings.Join(lines[1:], "\n")), -1)
	var footers []string
	for _, p := range slices.Backward(paragraphs) {
		if !footer.MatchString(p) {
			break // the body
		}
		footers = append(footers, strings.Split(p, "\n")...)
	}
	for _, l := range footers {
		if m := footer.FindStringSubmatch(l); m != nil && breaking.MatchString(m[1]) &&
			(m[1] != strings.ToUpper(m[1]) || m[2] != ": ") {
			return `"` + l + `" is not ` + "`BREAKING CHANGE: description`"
		}
	}
	return ""
}
