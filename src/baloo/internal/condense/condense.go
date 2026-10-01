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
	// Costs are the calls that added the most to the context, costliest first.
	Costs []Cost
	// Tokens is how many tokens each tool's calls added to the context.
	Tokens map[string]int
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

// Cost is a tool call, by its result's line `At`, that added `Tokens` tokens to the context.
type Cost struct {
	At     int
	Call   string
	Tokens int
}

const (
	promptChars = 300
	errorChars  = 200
	callChars   = 120
	repeatMin   = 3
	costMin     = 5000 // a call adding fewer tokens isn't worth a Retro's look
	topCosts    = 5
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
	Attachment json.RawMessage `json:"attachment"`
}

// result is a tool call's result, at the Transcript's line `at`, waiting for the next response's
// usage to tell what it cost.
type result struct {
	at         int
	call, tool string
	chars      int
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

// response is the id of the assistant's message `message`, the tokens of the context it was
// given and the tokens it wrote, from the usage Claude Code records; ok is false without one, and
// for a message Claude Code wrote itself, such as "No response requested.", whose usage is zeros.
func response(message json.RawMessage) (id string, context, output int, ok bool) {
	var m struct {
		ID    string `json:"id"`
		Model string `json:"model"`
		Usage *struct {
			Input         int `json:"input_tokens"`
			CacheCreation int `json:"cache_creation_input_tokens"`
			CacheRead     int `json:"cache_read_input_tokens"`
			Output        int `json:"output_tokens"`
		} `json:"usage"`
	}
	if json.Unmarshal(message, &m) != nil || m.Usage == nil || m.ID == "" || m.Model == "<synthetic>" {
		return "", 0, 0, false
	}
	u := m.Usage
	return m.ID, u.Input + u.CacheCreation + u.CacheRead, u.Output, true
}

// imageChars is what an image or a document counts as, in characters of text, whatever the size
// of its data: about 1,500 tokens, an estimate for a screenshot.
const imageChars = 6000

// size is how many characters of text the JSON `raw` holds, so that a result, a prompt and an
// attachment are measured alike: the length of its strings, but for the names of types, with an
// image or a document counted as imageChars.
func size(raw json.RawMessage) int {
	var v any
	if json.Unmarshal(raw, &v) != nil {
		return 0
	}
	var walk func(v any) int
	walk = func(v any) int {
		n := 0
		switch v := v.(type) {
		case string:
			n = len([]rune(v))
		case []any:
			for _, e := range v {
				n += walk(e)
			}
		case map[string]any:
			if v["type"] == "image" || v["type"] == "document" {
				return imageChars
			}
			for k, e := range v {
				if k != "type" {
					n += walk(e)
				}
			}
		}
		return n
	}
	return walk(v)
}

// charge spreads `tokens`, what the context grew by after the results `rs` and `other`
// characters of what else came (a prompt, Claude Code's attachments), over them by length: calls
// made in parallel come back to one response, and a call is charged only its own result's part.
func (s *Session) charge(rs []result, other, tokens int) {
	if len(rs) == 0 || tokens <= 0 {
		return
	}
	chars := other
	for _, r := range rs {
		chars += r.chars
	}
	for _, r := range rs {
		n := tokens / len(rs)
		if chars > 0 {
			n = tokens * r.chars / chars
		}
		if n <= 0 {
			continue
		}
		s.Tokens[r.tool] += n
		if n >= costMin {
			s.Costs = append(s.Costs, Cost{r.at, r.call, n})
		}
	}
}

// Condense is the session of the Transcript `transcript`, whose id is `id`.
func Condense(transcript []byte, id string) Session {
	s := Session{ID: id, Tools: map[string]int{}, Tokens: map[string]int{}}
	// The tool calls by id: each by what it acts on, and its tool.
	calls := map[string]struct{ call, tool string }{}
	counts := map[string]int{}
	// The last response's id, context and output, and the results given to the next one.
	prev, context, output, other := "", 0, 0, 0
	var pending []result
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
			if id, c, o, ok := response(l.Message); ok {
				if id != prev {
					// The context grew by the last response's output and what came after it.
					if prev != "" {
						s.charge(pending, other, c-context-output)
					}
					prev, pending, other = id, nil, 0
				}
				context, output = c, o
			}
			for _, b := range bs {
				if b.Type != "tool_use" || b.Name == "" {
					continue
				}
				s.Tools[b.Name]++
				c := call(b.Name, b.Input, cwd)
				calls[b.ID] = struct{ call, tool string }{c, b.Name}
				if slices.Contains(repeated, b.Name) {
					counts[c]++
				}
			}
		}
		results := slices.ContainsFunc(bs, func(b block) bool { return b.Type == "tool_result" })
		switch {
		case l.Type == "attachment":
			other += size(l.Attachment)
		case l.Type == "user" && !results:
			other += size(l.Message)
		}
		if l.Type != "user" || l.IsMeta {
			return true
		}
		if results {
			for _, b := range bs {
				if b.Type != "tool_result" {
					continue
				}
				c, ok := calls[b.ToolUseID]
				if !ok {
					c.call, c.tool = "?", "?"
				}
				pending = append(pending, result{at, c.call, c.tool, size(b.Content)})
				if b.IsError {
					text := textOf(content(b.Content))
					s.Events = append(s.Events, Event{At: at, Type: "error", Kind: kind(text), Call: c.call, Text: text})
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
	slices.SortStableFunc(s.Costs, func(a, b Cost) int { return b.Tokens - a.Tokens })
	s.Costs = s.Costs[:min(len(s.Costs), topCosts)]
	return s
}

// kilo is `n` tokens in thousands, `12k`.
func kilo(n int) string {
	return fmt.Sprintf("%dk", (n+500)/1000)
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
	if len(s.Costs) > 0 {
		out = append(out, "", "Expensive calls, by the tokens they added to the context:")
		for _, c := range s.Costs {
			out = append(out, fmt.Sprintf("[%d] %s %s", c.At, kilo(c.Tokens), clip(c.Call, callChars)))
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
// tool; the rest by their error), then the prompts typed more than once, which a skill or a Hook
// could take over, then the tools whose calls added the most tokens to the context.
func Summary(sessions []Session) string {
	var order []string
	byKind := map[string][]*seen{}
	var prompts []*seen
	tokens, in := map[string]int{}, map[string]int{}
	for _, s := range sessions {
		for tool, n := range s.Tokens {
			tokens[tool] += n
			in[tool]++
		}
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
	costliest := slices.SortedFunc(maps.Keys(tokens), func(a, b string) int {
		if tokens[a] != tokens[b] {
			return tokens[b] - tokens[a]
		}
		return strings.Compare(a, b)
	})
	if len(costliest) > 0 {
		out = append(out, "tokens added to the context, by tool:")
		for _, tool := range costliest[:min(len(costliest), top)] {
			out = append(out, fmt.Sprintf("  %s %s in %d session(s)", tool, kilo(tokens[tool]), in[tool]))
		}
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
