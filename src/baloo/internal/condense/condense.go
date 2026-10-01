// Package condense condenses Claude Code's Transcripts into what a Retro needs, masking anything
// that may be a Secret (ADR transcripts).
package condense

// cspell:ignore ermission

import (
	"bytes"
	"encoding/json"
	"fmt"
	"maps"
	"regexp"
	"slices"
	"strings"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/checks"
	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Session is what a Retro needs of one session's Transcript.
type Session struct {
	ID, Title string
	// Start is when the session started, `YYYY-MM-DD hh:mm` UTC; Minutes, how long it ran.
	Start    string
	Minutes  int
	Headless bool
	// Tools is how many calls of each tool the session made.
	Tools  map[string]int
	Events []Event
	// Repeats are the calls made at least three times, commonest first.
	Repeats []Repeat
}

// Event is a moment of a session a Retro looks at, by the Transcript's line `At`, from 1.
type Event struct {
	At int
	// Type is prompt, command, interrupt or error.
	Type string
	// Kind is an error's: check, rejected, hook, classifier, permission, stale, exit or other.
	Kind string
	// Call is the failed tool call, by what it acts on: `Bash(go test ./...)`.
	Call string
	Text string
}

// Repeat is a tool call made N times.
type Repeat struct {
	Call string
	N    int
}

const (
	promptChars = 300
	errorChars  = 200
	callChars   = 120
	repeatMin   = 3
)

// repeated are the tools whose repeated calls show Claude hunting for the same thing.
var repeated = []string{"Bash", "Read", "Grep", "Glob", "WebFetch"}

type line struct {
	Type       string          `json:"type"`
	IsMeta     bool            `json:"isMeta"`
	Entrypoint string          `json:"entrypoint"`
	Timestamp  string          `json:"timestamp"`
	Cwd        string          `json:"cwd"`
	AITitle    string          `json:"aiTitle"`
	Message    json.RawMessage `json:"message"`
}

type block struct {
	Type      string          `json:"type"`
	Text      string          `json:"text"`
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	Input     map[string]any  `json:"input"`
	ToolUseID string          `json:"tool_use_id"`
	IsError   bool            `json:"is_error"`
	Content   json.RawMessage `json:"content"`
}

// lines calls `each` with each JSON line of the Transcript `transcript`, numbered from 1; a line
// that isn't JSON is skipped and not counted.
func lines(transcript []byte, each func(at int, l line) bool) {
	at := 0
	for _, raw := range bytes.Split(transcript, []byte("\n")) {
		var l line
		if json.Unmarshal(raw, &l) != nil {
			continue
		}
		at++
		if !each(at, l) {
			return
		}
	}
}

// blocks are the content blocks of a message `message`, a string's as one text block.
func blocks(message json.RawMessage) []block {
	var m struct {
		Content json.RawMessage `json:"content"`
	}
	if json.Unmarshal(message, &m) != nil {
		return nil
	}
	return content(m.Content)
}

// content is the blocks of `raw`, a string or a list of blocks.
func content(raw json.RawMessage) []block {
	var text string
	if json.Unmarshal(raw, &text) == nil {
		return []block{{Type: "text", Text: text}}
	}
	var bs []block
	json.Unmarshal(raw, &bs)
	return bs
}

// textOf is the text of the blocks `bs`.
func textOf(bs []block) string {
	var texts []string
	for _, b := range bs {
		if b.Type == "text" {
			texts = append(texts, b.Text)
		}
	}
	return strings.Join(texts, "\n")
}

var (
	commandName = regexp.MustCompile(`<command-name>(.*?)</command-name>`)
	commandArgs = regexp.MustCompile(`(?s)<command-args>(.*?)</command-args>`)
	notHuman    = regexp.MustCompile(`^<(local-command|task-notification|system-reminder)`)
)

// human is the type of the event the text `text` of the user's turn is: prompt, command or
// interrupt; "" for what Claude Code wrote there.
func human(text string) string {
	switch {
	case strings.HasPrefix(text, "[Request interrupted by user"):
		return "interrupt"
	case strings.HasPrefix(text, "<command-name>"), strings.HasPrefix(text, "<command-message>"):
		return "command"
	case notHuman.MatchString(text), strings.HasPrefix(text, "Base directory for this skill:"):
		return ""
	case strings.TrimSpace(text) != "":
		return "prompt"
	}
	return ""
}

// commandText is the command the user typed, `/name args`, from what Claude Code wrote of it.
func commandText(text string) string {
	name, args := "", ""
	if m := commandName.FindStringSubmatch(text); m != nil {
		name = m[1]
	}
	if m := commandArgs.FindStringSubmatch(text); m != nil {
		args = m[1]
	}
	return strings.TrimSpace(name + " " + args)
}

// Condense is the session of the Transcript `transcript`, whose id is `id`.
func Condense(transcript []byte, id string) Session {
	s := Session{ID: id, Tools: map[string]int{}}
	calls := map[string]string{}
	counts := map[string]int{}
	var first, last time.Time
	cwd := ""
	lines(transcript, func(at int, l line) bool {
		if l.AITitle != "" {
			s.Title = l.AITitle
		}
		if l.Cwd != "" {
			cwd = l.Cwd
		}
		if l.Entrypoint == "sdk-cli" {
			s.Headless = true
		}
		if t, err := time.Parse(time.RFC3339, l.Timestamp); err == nil {
			if first.IsZero() || t.Before(first) {
				first = t
			}
			if t.After(last) {
				last = t
			}
		}
		bs := blocks(l.Message)
		if l.Type == "assistant" {
			for _, b := range bs {
				if b.Type != "tool_use" || b.Name == "" {
					continue
				}
				s.Tools[b.Name]++
				c := call(b.Name, b.Input, cwd)
				calls[b.ID] = c
				if slices.Contains(repeated, b.Name) {
					counts[c]++
				}
			}
		}
		if l.Type != "user" || l.IsMeta {
			return true
		}
		if slices.ContainsFunc(bs, func(b block) bool { return b.Type == "tool_result" }) {
			for _, b := range bs {
				if b.Type == "tool_result" && b.IsError {
					text := textOf(content(b.Content))
					c, ok := calls[b.ToolUseID]
					if !ok {
						c = "?"
					}
					s.Events = append(s.Events, Event{At: at, Type: "error", Kind: kind(text), Call: c, Text: text})
				}
			}
			return true
		}
		text := textOf(bs)
		switch typ := human(text); typ {
		case "interrupt":
			s.Events = append(s.Events, Event{At: at, Type: typ})
		case "command":
			s.Events = append(s.Events, Event{At: at, Type: typ, Text: commandText(text)})
		case "prompt":
			s.Events = append(s.Events, Event{At: at, Type: typ, Text: text})
		}
		return true
	})
	if !first.IsZero() {
		s.Start = first.UTC().Format("2006-01-02 15:04")
		s.Minutes = int(last.Sub(first).Round(time.Minute).Minutes())
	}
	for c, n := range counts {
		if n >= repeatMin {
			s.Repeats = append(s.Repeats, Repeat{c, n})
		}
	}
	slices.SortFunc(s.Repeats, func(a, b Repeat) int {
		if a.N != b.N {
			return b.N - a.N
		}
		return strings.Compare(a.Call, b.Call)
	})
	return s
}

// kinds are the kinds of a failed tool call, by its error; the first that matches names it.
var kinds = []struct {
	kind string
	re   *regexp.Regexp
}{
	{"check", regexp.MustCompile(`hook error: ` + names.Plugin + `:[a-z-]+: `)},
	{"rejected", regexp.MustCompile(`doesn't want to proceed|User rejected`)},
	{"hook", regexp.MustCompile(`hook error`)},
	{"classifier", regexp.MustCompile(`auto mode classifier|auto mode cannot`)},
	{"permission", regexp.MustCompile(`requires? approval|[Pp]ermission to use .* (denied|has been denied)|was blocked\. For security`)},
	{"stale", regexp.MustCompile(`modified since read|has not been read yet`)},
	{"exit", regexp.MustCompile(`^Exit code \d+`)},
}

// kind is the kind of a tool call that failed with `error`.
func kind(error string) string {
	for _, k := range kinds {
		if k.re.MatchString(error) {
			return k.kind
		}
	}
	return "other"
}

// callKeys are the inputs that say what a tool call acts on, the likeliest first.
var callKeys = []string{"command", "file_path", "path", "pattern", "skill", "url", "description"}

// call is a tool call by what it acts on, a path from the folder `cwd` where it is in it:
// `Bash(go test ./...)`, `Read(src/x.go)`.
func call(name string, input map[string]any, cwd string) string {
	text := ""
	for _, key := range append(callKeys, slices.Sorted(maps.Keys(input))...) {
		if v, ok := input[key].(string); ok {
			text = v
			break
		}
	}
	if cwd != "" {
		text = strings.TrimPrefix(text, cwd+"/")
	}
	return name + "(" + text + ")"
}

// clip is `text` on one line, cut to `max` characters.
func clip(text string, max int) string {
	flat := strings.Join(strings.Fields(text), " ")
	if r := []rune(flat); len(r) > max {
		return string(r[:max-1]) + "…"
	}
	return flat
}

// gist is the failure's error, cut to `max` characters: for a failed command, its end, where its
// own error usually is.
func gist(e Event, max int) string {
	if e.Kind != "exit" {
		return clip(e.Text, max)
	}
	code, rest, _ := strings.Cut(e.Text, "\n")
	tail := []rune(strings.Join(strings.Fields(rest), " "))
	if len(tail) > max {
		return code + ": …" + string(tail[len(tail)-max:])
	}
	return code + ": " + string(tail)
}

func (e Event) String() string {
	head := fmt.Sprintf("[%d] %s", e.At, e.Type)
	switch e.Type {
	case "interrupt":
		return head
	case "error":
		return fmt.Sprintf("%s %s %s: %s", head, e.Kind, clip(e.Call, callChars), gist(e, errorChars))
	}
	return head + ": " + clip(e.Text, promptChars)
}

// Report is the session `s` for a Retro, masked.
func (s Session) Report() string {
	calls, failed := 0, 0
	for _, n := range s.Tools {
		calls += n
	}
	for _, e := range s.Events {
		if e.Type == "error" {
			failed++
		}
	}
	tools := slices.SortedFunc(maps.Keys(s.Tools), func(a, b string) int {
		if s.Tools[a] != s.Tools[b] {
			return s.Tools[b] - s.Tools[a]
		}
		return strings.Compare(a, b)
	})
	var used []string
	for _, name := range tools {
		used = append(used, fmt.Sprintf("%s %d", name, s.Tools[name]))
	}
	if used == nil {
		used = []string{"none"}
	}
	head := "# Session " + s.ID
	if s.Title != "" {
		head += ": " + s.Title
	}
	out := []string{head, fmt.Sprintf("%s, %d min, %d tool calls, %d failed", s.Start, s.Minutes,
		calls, failed), "Tools: " + strings.Join(used, ", "), ""}
	for _, e := range s.Events {
		out = append(out, e.String())
	}
	if len(s.Repeats) > 0 {
		out = append(out, "", "Repeated calls:")
		for _, r := range s.Repeats {
			out = append(out, fmt.Sprintf("%d× %s", r.N, clip(r.Call, callChars)))
		}
	}
	return Mask(strings.Join(out, "\n"))
}

var (
	privateKey = regexp.MustCompile(`(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*KEY-----|$)`)
	// token is a long run of the characters a token is made of: an API key, a JWT's part.
	token  = regexp.MustCompile(`[A-Za-z0-9_+-]{32,}`)
	letter = regexp.MustCompile(`[A-Za-z]`)
	digit  = regexp.MustCompile(`[0-9]`)
	hex    = regexp.MustCompile(`^[0-9a-fA-F-]+$`)
)

// Mask is `text` with anything that may be a Secret replaced by `*****`: a private key's block,
// each kind of Secret no-secrets-in-commits knows, and a long run of letters and digits mixed,
// but not hex, such as a commit or a session's id (ADR transcripts).
func Mask(text string) string {
	const mask = "*****"
	text = privateKey.ReplaceAllLiteralString(text, mask)
	text = checks.MaskSecrets(text, mask)
	return token.ReplaceAllStringFunc(text, func(s string) string {
		if letter.MatchString(s) && digit.MatchString(s) && !hex.MatchString(s) {
			return mask
		}
		return s
	})
}

const (
	promptMin  = 20 // shorter prompts ("yes", "commit it") repeat without meaning much
	top        = 5  // the commonest failures of each kind shown
	topPrompts = 10
)

// seen is how often one failure or prompt came up, and in which sessions.
type seen struct {
	key string
	n   int
	ids map[string]bool
}

// tally adds `key` of the session `id` to `counts`, in the order keys first come.
func tally(counts []*seen, key, id string) []*seen {
	for _, c := range counts {
		if c.key == key {
			c.n++
			c.ids[id] = true
			return counts
		}
	}
	return append(counts, &seen{key, 1, map[string]bool{id: true}})
}

// commonest sorts `counts` by how often each came up, keeping the first seen first among equals.
func commonest(counts []*seen) []*seen {
	slices.SortStableFunc(counts, func(a, b *seen) int { return b.n - a.n })
	return counts
}

// Summary is the sessions `sessions` together, for a Retro, masked: their failures by kind, with
// the commonest of each (a failed command, a call rejected or refused by the classifier, by its
// tool; the rest by their error), then the prompts typed more than once, which a skill or a hook
// could take over.
func Summary(sessions []Session) string {
	var order []string
	byKind := map[string][]*seen{}
	var prompts []*seen
	for _, s := range sessions {
		for _, e := range s.Events {
			switch e.Type {
			case "error":
				key := clip(e.Text, 100)
				if e.Kind == "exit" || e.Kind == "rejected" || e.Kind == "classifier" {
					key, _, _ = strings.Cut(e.Call, "(")
				}
				if byKind[e.Kind] == nil {
					order = append(order, e.Kind)
				}
				byKind[e.Kind] = tally(byKind[e.Kind], key, s.ID)
			case "prompt":
				if text := clip(strings.ToLower(e.Text), 100); len(text) >= promptMin {
					prompts = tally(prompts, text, s.ID)
				}
			}
		}
	}
	total := func(kind string) (n int) {
		for _, c := range byKind[kind] {
			n += c.n
		}
		return n
	}
	slices.SortStableFunc(order, func(a, b string) int { return total(b) - total(a) })
	out := []string{fmt.Sprintf("# Across %d sessions", len(sessions))}
	for _, kind := range order {
		out = append(out, fmt.Sprintf("%s: %d", kind, total(kind)))
		for i, c := range commonest(byKind[kind]) {
			if i == top {
				break
			}
			out = append(out, fmt.Sprintf("  %d× in %d session(s): %s", c.n, len(c.ids), c.key))
		}
	}
	var repeats []string
	for _, c := range commonest(prompts) {
		if c.n > 1 && len(repeats) < topPrompts {
			repeats = append(repeats, fmt.Sprintf("  %d× %s", c.n, c.key))
		}
	}
	if len(repeats) > 0 {
		out = append(append(out, "repeated prompts:"), repeats...)
	}
	return Mask(strings.Join(out, "\n"))
}

// aroundChars is the most of one block Around shows.
const aroundChars = 2000

// Around is the lines of the Transcript `transcript` within `radius` of its line `at`, numbered
// as in a Report: their text, tool calls and results, each cut to `aroundChars`, masked. It is
// what a Retro reads instead of the raw Transcript, so a Secret an earlier session printed
// doesn't reach one more context (ADR transcripts).
func Around(transcript []byte, at, radius int) string {
	full := func(text string) string {
		if r := []rune(text); len(r) > aroundChars {
			return string(r[:aroundChars])
		}
		return text
	}
	var out []string
	cwd := ""
	lines(transcript, func(n int, l line) bool {
		if l.Cwd != "" {
			cwd = l.Cwd
		}
		if n < at-radius {
			return true
		}
		if n > at+radius {
			return false
		}
		head := fmt.Sprintf("[%d] %s", n, l.Type)
		for _, b := range blocks(l.Message) {
			switch {
			case b.Type == "text" && strings.TrimSpace(b.Text) != "":
				out = append(out, head+": "+full(b.Text))
			case b.Type == "tool_use":
				out = append(out, head+" calls "+call(b.Name, b.Input, cwd))
			case b.Type == "tool_result":
				failed := ""
				if b.IsError {
					failed = " (failed)"
				}
				out = append(out, head+" result"+failed+": "+full(textOf(content(b.Content))))
			}
		}
		return true
	})
	return Mask(strings.Join(out, "\n"))
}

// Conversation is the user's and Claude's text in the Transcript `transcript`, for a Session
// review, masked, then cut to its last `max` characters: no tool call or result, and of what
// Claude Code wrote in the user's turn only the commands (ADR session-review).
func Conversation(transcript []byte, max int) string {
	var out []string
	lines(transcript, func(_ int, l line) bool {
		text := textOf(blocks(l.Message))
		switch {
		case l.Type == "assistant" && strings.TrimSpace(text) != "":
		case l.Type != "user" || l.IsMeta:
			return true
		case human(text) == "prompt":
		case human(text) == "command":
			text = commandText(text)
		default:
			return true
		}
		out = append(out, l.Type+": "+text)
		return true
	})
	text := []rune(Mask(strings.Join(out, "\n\n")))
	if len(text) > max {
		text = text[len(text)-max:]
	}
	return string(text)
}
