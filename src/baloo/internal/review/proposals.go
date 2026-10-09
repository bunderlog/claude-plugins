package review

import (
	"bufio"
	"errors"
	"fmt"
	"io/fs"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// The user's decisions on a Proposal, as the log records them.
const (
	Accepted = "accepted"
	// AcceptedEdited is accepted with the text changed as it was applied, in the Proposal's
	// Applied; it counts as accepted.
	AcceptedEdited = "accepted-edited"
	Rejected       = "rejected"
	Deferred       = "deferred"
)

// maxDeferred is how many times a Proposal can be deferred; then it is accepted or rejected.
const maxDeferred = 2

// Proposal is one change a Session review proposes to .about/: its review's and its own id, its
// target (inbox, glossary, adr or prd), its kind (add, edit or delete), the file it changes, a
// title, the text it changes and the text it puts there, and the text put there instead where it
// was applied changed, which Claude adds; the review's After stays as it proposed it. Problem says
// why the file can't be read as a Proposal, or is "".
type Proposal struct {
	Review, ID, Target, Kind, Path, Title string
	Before, After, Applied                string
	Problem                               string
}

// accepted says whether the decision `d` accepts the Proposal, as proposed or edited.
func accepted(d string) bool { return d == Accepted || d == AcceptedEdited }

// Item is a Proposal with what the user decided of it, from the log, and how it stands with its
// file: Stale when the text it changes is no longer there, Mismatch when the log and the file
// disagree.
type Item struct {
	Proposal
	Decision string // the last one, "" for none
	Deferred int
	Stale    bool
	Mismatch string
}

// Pending says whether the item still waits for the user's decision.
func (it Item) Pending() bool { return it.Decision == "" || it.Decision == Deferred }

var heading = regexp.MustCompile(`^## (P\d+) · (\S+) · (\S+) · (\S+) · (.+)$`)

// Parse reads the Proposals of the review `review` from the text of its file. A block is fenced
// with ~~~, as the review is asked to write it, or with ```, as a reviewer may write it anyway.
func Parse(review string, text []byte) []Proposal {
	var list []Proposal
	var block *string
	fence := "" // the open block's fence, "" outside one
	for _, line := range strings.Split(string(text), "\n") {
		p := len(list) - 1
		switch {
		case fence != "" && line == fence:
			fence = ""
		case fence != "":
			*block += line + "\n"
		case strings.HasPrefix(line, "## "):
			block = nil
			m := heading.FindStringSubmatch(line)
			if m == nil {
				list = append(list, Proposal{Review: review, Title: strings.TrimPrefix(line, "## "),
					Problem: "its heading is not ## <id> · <target> · <kind> · <path> · <title>"})
				continue
			}
			list = append(list, Proposal{Review: review, ID: m[1], Target: m[2], Kind: m[3], Path: m[4],
				Title: m[5]})
		case p < 0:
		case line == "Before:":
			block = &list[p].Before
		case line == "After:":
			block = &list[p].After
		case line == "Applied:":
			block = &list[p].Applied
		case block != nil && (strings.HasPrefix(line, "~~~") || strings.HasPrefix(line, "```")):
			fence = line[:3]
		}
	}
	for i := range list {
		if list[i].Problem == "" {
			list[i].Problem = invalid(list[i])
		}
	}
	return list
}

// invalid says why `p` is not a Proposal the user can decide, or "".
func invalid(p Proposal) string {
	file := map[string]func(string) bool{
		"inbox":    func(path string) bool { return path == names.Inbox },
		"glossary": func(path string) bool { return path == names.Glossary },
		"adr":      within(names.ADRs),
		"prd":      within(names.PRDs),
	}[p.Target]
	switch {
	case file == nil:
		return "its target is not inbox, glossary, adr or prd"
	case !file(p.Path):
		return "its path is not a file of its target"
	case p.Kind == "add" && (p.After == "" || p.Before != ""):
		return "an add has After and no Before"
	case p.Kind == "edit" && (p.After == "" || p.Before == ""):
		return "an edit has Before and After"
	case p.Kind == "delete" && (p.Before == "" || p.After != ""):
		return "a delete has Before and no After"
	case p.Kind != "add" && p.Kind != "edit" && p.Kind != "delete":
		return "its kind is not add, edit or delete"
	case p.Kind == "delete" && p.Applied != "":
		return "a delete has no Applied"
	}
	return ""
}

// within says whether a path is a Markdown file right in the folder `dir`.
func within(dir string) func(string) bool {
	return func(path string) bool {
		name, ok := strings.CutPrefix(path, dir)
		return ok && name != ".md" && strings.HasSuffix(name, ".md") && !strings.Contains(name, "/")
	}
}

// Repo is how the log names the repo at `root`, the same on every machine: its origin's URL,
// without a user or password, or its root where it has none.
func Repo(root string) string {
	out, err := exec.Command("git", "-C", root, "remote", "get-url", "origin").Output()
	remote := strings.TrimSpace(string(out))
	if err != nil || remote == "" {
		return root
	}
	if u, err := url.Parse(remote); err == nil && u.Scheme != "" {
		u.User = nil
		return u.String()
	}
	return remote
}

// logFile is the log of the user's decisions, in the plugin's data folder `data`: a line per
// decision, its fields split by tabs: when (UTC), the repo, the review, the Proposal, its target,
// its kind and the decision.
func logFile(data string) string {
	return filepath.Join(data, "session-review", "session-review.log")
}

const logFields = 7

// decisions are the decisions the log holds for the repo `repo`, by review and Proposal: the last
// one, and how many times it was deferred.
func decisions(data, repo string) map[string]Item {
	got := map[string]Item{}
	f, err := os.Open(logFile(data))
	if err != nil {
		return got
	}
	defer f.Close()
	lines := bufio.NewScanner(f)
	for lines.Scan() {
		field := strings.Split(lines.Text(), "\t")
		if len(field) != logFields || field[1] != repo {
			continue
		}
		key := field[2] + "/" + field[3]
		it := got[key]
		it.Decision = field[6]
		if it.Decision == Deferred {
			it.Deferred++
		}
		got[key] = it
	}
	return got
}

// Items are the Proposals in the repo at `root`, each with what the log says of it and how it
// stands with its file, in the order of their reviews.
func Items(root, data string) []Item {
	files, _ := filepath.Glob(filepath.Join(root, names.Proposals, "*.md"))
	if len(files) == 0 {
		return nil
	}
	slices.Sort(files)
	logged := decisions(data, Repo(root))
	var items []Item
	for _, file := range files {
		text, err := os.ReadFile(file)
		if err != nil {
			continue
		}
		for _, p := range Parse(strings.TrimSuffix(filepath.Base(file), ".md"), text) {
			it := logged[p.Review+"/"+p.ID]
			it.Proposal = p
			if p.Problem == "" {
				target, _ := os.ReadFile(filepath.Join(root, p.Path))
				stands(&it, string(target))
			}
			items = append(items, it)
		}
	}
	return items
}

// stands sets how the item `it` stands with the text `target` of its file.
func stands(it *Item, target string) {
	has := func(block string) bool { return strings.Contains(flat(target), flat(block)) }
	put := it.After
	if it.Applied != "" {
		put = it.Applied
	}
	applied := has(put)
	if it.Kind == "delete" {
		applied = !has(it.Before)
	}
	switch {
	case accepted(it.Decision) && !applied && it.Kind == "delete":
		it.Mismatch = "accepted, but its Before is still in " + it.Path
	case accepted(it.Decision) && !applied:
		it.Mismatch = "accepted, but its " + block(it) + " is not in " + it.Path
	case it.Pending() && it.Kind != "delete" && applied:
		it.Mismatch = "its " + block(it) + " is in " + it.Path + ", but no decision is logged"
	case it.Pending() && it.Kind != "add" && !has(it.Before):
		it.Stale = true
	}
}

// block names the text the item puts in its file: its Applied where it has one.
func block(it *Item) string {
	if it.Applied != "" {
		return "Applied"
	}
	return "After"
}

// flat is `text` with each run of white space one space, so a rewrapped line still matches.
func flat(text string) string { return strings.Join(strings.Fields(text), " ") }

// Decide logs the user's decision `decision` on the Proposal `id` of the review `review` in the
// repo at `root`, and deletes the review's file once each of its Proposals is decided and in its
// file as decided. It returns what Claude should still do, or "", and an error where the decision
// can't be logged: an unknown Proposal, a third deferral, or accepting a stale edit.
func Decide(root, data, review, id, decision string) (string, error) {
	if !accepted(decision) && decision != Rejected && decision != Deferred {
		return "", fmt.Errorf("%s is not %s, %s, %s or %s", decision, Accepted, AcceptedEdited,
			Rejected, Deferred)
	}
	items := Items(root, data)
	at := slices.IndexFunc(items, func(it Item) bool { return it.Review == review && it.ID == id })
	if at < 0 {
		return "", fmt.Errorf("no proposal %s in %s%s.md", id, names.Proposals, review)
	}
	it := items[at]
	switch {
	case decision == Deferred && it.Deferred >= maxDeferred:
		return "", fmt.Errorf("%s was deferred %d times already: accept or reject it", id, it.Deferred)
	case decision == AcceptedEdited && it.Applied == "":
		return "", fmt.Errorf("%s has no Applied block: add one of the text you applied first, or log %s",
			id, Accepted)
	case accepted(decision) && it.Problem != "":
		return "", fmt.Errorf("%s can't be read (%s): fix it in its file first, or reject it", id, it.Problem)
	case accepted(decision) && it.Stale && it.Kind != "delete": // a delete applied looks stale too
		return "", fmt.Errorf("%s is stale, its Before no longer in %s: fix it in its file by hand "+
			"first, or reject it", id, it.Path)
	}
	if err := appendLog(data, Repo(root), it.Proposal, decision); err != nil {
		return "", err
	}
	items[at].Decision = decision
	target, _ := os.ReadFile(filepath.Join(root, it.Path))
	items[at].Mismatch = ""
	stands(&items[at], string(target))
	if err := tidy(root, data, review, items); err != nil {
		return "", err
	}
	if items[at].Mismatch != "" {
		return fmt.Sprintf("%s %s: %s: apply it, or add an Applied block of what you applied to it "+
			"and log %s", review, id, items[at].Mismatch, AcceptedEdited), nil
	}
	return "", nil
}

// appendLog adds the decision `decision` on `p` in the repo `repo` to the log. A log written before
// it had fields is moved aside once, to session-review.log.old, so every line parses.
func appendLog(data, repo string, p Proposal, decision string) error {
	file := logFile(data)
	if err := os.MkdirAll(filepath.Dir(file), 0o700); err != nil {
		return err
	}
	if f, err := os.Open(file); err == nil {
		first := bufio.NewScanner(f)
		old := first.Scan() && len(strings.Split(first.Text(), "\t")) != logFields
		f.Close()
		if old {
			if err := os.Rename(file, file+".old"); err != nil {
				return err
			}
		}
	}
	line := strings.Join([]string{time.Now().UTC().Format(time.RFC3339), repo, p.Review, p.ID,
		p.Target, p.Kind, decision}, "\t")
	f, err := os.OpenFile(file, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0o600)
	if err != nil {
		return err
	}
	_, err = f.WriteString(line + "\n")
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	return err
}

// tidy moves the file of the review `review` out of the repo, into the review's folder in the
// plugin's data folder `data`, decided/, once each of its Proposals in `items` is accepted or
// rejected and none disagrees with its file; the repo's folder goes with its last file. It is kept
// there for good, for a later measurement to judge the Proposals by.
func tidy(root, data, review string, items []Item) error {
	for _, it := range items {
		if it.Review == review && (it.Pending() || it.Mismatch != "") {
			return nil
		}
	}
	decided := filepath.Join(folder(root, data), "decided")
	if err := os.MkdirAll(decided, 0o700); err != nil {
		return err
	}
	from := filepath.Join(root, names.Proposals, review+".md")
	if err := os.Rename(from, filepath.Join(decided, review+".md")); err != nil {
		return err
	}
	os.Remove(filepath.Join(root, names.Proposals)) // only when empty
	return nil
}

// Show is what to tell Claude of the Proposals waiting in the repo at `root`, and of where the log
// and the files disagree, that the session `session` hasn't been told yet; nil when nothing is new.
// `decide` is the command that logs a decision. A headless session is told nothing, and showing
// consumes nothing: a Proposal waits until it is decided.
func Show(root, data, session, decide string) []string {
	if Headless() {
		return nil
	}
	dir := filepath.Join(data, "session-review", "shown")
	forget(dir)
	seen := filepath.Join(dir, session)
	told, _ := os.ReadFile(seen)
	known := strings.Split(string(told), "\n")
	var proposals, mismatches, keys []string
	for _, it := range Items(root, data) {
		key := it.Review + "/" + it.ID
		switch {
		case it.Mismatch != "":
			key = "mismatch " + key
			if !slices.Contains(known, key) {
				mismatches = append(mismatches, fmt.Sprintf("  mismatch: %s %s, %s", it.Review, it.ID, it.Mismatch))
				keys = append(keys, key)
			}
		case it.Pending() && !slices.Contains(known, key):
			proposals = append(proposals, "  "+line(it))
			keys = append(keys, key)
		}
	}
	if len(keys) == 0 {
		return nil
	}
	var lines []string
	if len(proposals) > 0 {
		lines = append(lines, "Session review proposals for .about/ wait for the user, in "+names.Proposals+
			"<review>.md: show the user this list and ask, for each, accept, reject or defer, "+
			"after reading its file for the full edit; recommend reject for a stale one, and "+
			"offer no defer for one deferred twice. Apply each accepted one: a glossary, adr or prd "+
			"one through the "+names.Plugin+":glossary, "+names.Plugin+":adr or "+names.Plugin+
			":prd skill, an inbox one by its edit as written; where what you applied differs from "+
			"its After, add to the Proposal an Applied: block of the text you applied, fenced as After "+
			"is, and log accepted-edited. Then log each answer with `"+decide+
			" <review> <id> accepted|accepted-edited|rejected|deferred`")
		lines = append(lines, proposals...)
	}
	if len(mismatches) > 0 {
		lines = append(lines, "Session review proposals whose log and file disagree: tell the user, "+
			"and fix the file or log the decision")
		lines = append(lines, mismatches...)
	}
	if session != "" {
		os.MkdirAll(dir, 0o700)
		os.WriteFile(seen, []byte(strings.Join(append(known, keys...), "\n")), 0o600)
	}
	return lines
}

// line is the item `it` as Claude is shown it.
func line(it Item) string {
	if it.Problem != "" {
		return fmt.Sprintf("%s %s: can't be read, %s: %s", it.Review, it.ID, it.Problem, it.Title)
	}
	text := fmt.Sprintf("%s %s %s %s %s: %s", it.Review, it.ID, it.Target, it.Kind, it.Path, it.Title)
	if it.Stale {
		text += " (stale: its Before is no longer in its file)"
	}
	if it.Deferred > 0 {
		text += fmt.Sprintf(" (deferred %d×)", it.Deferred)
	}
	return text
}

// forget deletes what sessions were told more than a week ago.
func forget(dir string) {
	entries, err := os.ReadDir(dir)
	if errors.Is(err, fs.ErrNotExist) {
		return
	}
	for _, e := range entries {
		if info, err := e.Info(); err == nil && time.Since(info.ModTime()) > kept {
			os.Remove(filepath.Join(dir, e.Name()))
		}
	}
}
