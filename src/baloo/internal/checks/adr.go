package checks

import (
	"regexp"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// adrDate is an ADR's Date line, ending in LF or CRLF, with `Status: proposed` on the line above it
// for a draft.
var adrDate = regexp.MustCompile(`(?m)^(Status: proposed\n)?Date: *(.*?) *\r?$`)

// NoStaleADRDate is the Check baloo:no-stale-adr-date (pre-commit): `<path>: <why>` for each
// accepted ADR the staged changes of the repo `dir` change without setting its Date to `today`,
// YYYY-MM-DD. A new ADR, a deleted or renamed one and a draft pass. It errs where git does, such
// as outside a repo.
func NoStaleADRDate(dir, today string) ([]string, error) {
	list, err := git(dir, "diff", "--cached", "--no-renames", "--diff-filter=M", "--name-only", "-z",
		"--", names.ADRs+"*.md")
	if err != nil {
		return nil, err
	}
	var found []string
	for _, path := range strings.Split(strings.TrimSuffix(list, "\x00"), "\x00") {
		if path == "" {
			continue
		}
		text, err := git(dir, "cat-file", "blob", ":"+path)
		if err != nil {
			return nil, err
		}
		switch m := adrDate.FindStringSubmatch(text); {
		case m == nil:
			found = append(found, path+": has no Date line; add Date: "+today+" under its title")
		case m[1] == "" && m[2] != today:
			found = append(found, path+": changed, but its Date is "+m[2]+"; set it to "+today)
		}
	}
	return found, nil
}
