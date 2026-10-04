package statusline

import (
	"fmt"
	"math"
	"os/exec"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

// Input is what Claude Code gives a status line command on stdin, the part the Status line shows.
type Input struct {
	Workspace struct {
		CurrentDir string `json:"current_dir"`
	} `json:"workspace"`
	Model struct {
		DisplayName string `json:"display_name"`
	} `json:"model"`
	Effort struct {
		Level string `json:"level"`
	} `json:"effort"`
	// ContextWindow is nil before Claude Code has one.
	ContextWindow *struct {
		UsedPercentage   *float64 `json:"used_percentage"`
		TotalInputTokens float64  `json:"total_input_tokens"`
	} `json:"context_window"`
	// PromptCache is nil before the main conversation's first reply.
	PromptCache *PromptCache `json:"prompt_cache"`
	RateLimits  struct {
		FiveHour Limit `json:"five_hour"`
		SevenDay Limit `json:"seven_day"`
	} `json:"rate_limits"`
}

// Limit is one of the rate limits; a field Claude Code doesn't give is nil.
type Limit struct {
	UsedPercentage *float64 `json:"used_percentage"`
	ResetsAt       *float64 `json:"resets_at"`
}

// PromptCache is the main conversation's prompt cache; a field Claude Code doesn't give is nil.
type PromptCache struct {
	Warm bool `json:"warm"`
	// CachingObserved is false while no reply has used the cache: caching is off.
	CachingObserved bool     `json:"caching_observed"`
	TTL             string   `json:"ttl"`
	ExpiresAt       *float64 `json:"expires_at"`
	// RecacheTokensIfCold is the cache's size: what the next request writes to it again once it
	// is cold; nil right after a compaction.
	RecacheTokensIfCold *float64 `json:"recache_tokens_if_cold"`
}

// Bars are the Status line's bars, by their names in the Config, in the order it shows them
// without one.
var Bars = []string{"context", "cache", "5h", "7d"}

// Thresholds are the percentages at which a bar turns yellow and red: for a Usage bar, of what is
// used, from them up; for the Cache bar, of the cache's lifetime left, below them.
type Thresholds struct{ Yellow, Red int }

// Ordered says whether `t` turns the bar `name` yellow before red.
func Ordered(name string, t Thresholds) bool {
	if name == "cache" {
		return t.Yellow >= t.Red
	}
	return t.Yellow <= t.Red
}

// Layout is the bars the Status line shows, in order, and each one's Thresholds.
type Layout struct {
	Bars       []string
	Thresholds map[string]Thresholds
}

// Default is the Layout where the Config sets none: every bar, at the thresholds of ADR
// status-line.
func Default() Layout {
	return Layout{slices.Clone(Bars), map[string]Thresholds{
		"context": {15, 20}, "cache": {40, 20}, "5h": {70, 85}, "7d": {80, 95},
	}}
}

// lifetimes are the seconds a cached prefix stays warm, by its TTL.
var lifetimes = map[string]float64{"5m": 300, "1h": 3600}

// now is the clock the Cache bar counts down by.
var now = time.Now

const reset = "\x1b[00m"

func paint(code, text string) string { return "\x1b[" + code + "m" + text + reset }
func label(text string) string       { return paint("2;37", text) }

// blocks is a bar `width` wide, `pct` percent of it filled.
func blocks(pct, width int) string {
	filled := pct * width / 100
	return strings.Repeat("█", filled) + strings.Repeat("░", width-filled)
}

// bar is a Usage bar `width` wide and its percentage: dim green, yellow and red from `t`.
func bar(percent float64, width int, t Thresholds) string {
	pct := int(min(100, max(0, math.Round(percent))))
	color := "2;32"
	switch {
	case pct >= t.Red:
		color = "2;31"
	case pct >= t.Yellow:
		color = "2;33"
	}
	return paint(color, blocks(pct, width)) + " " + strconv.Itoa(pct) + "%"
}

// thousands is `tokens` in thousands, as "(120K)".
func thousands(tokens float64) string {
	return paint("2;90", fmt.Sprintf("(%dK)", int(math.Round(tokens/1000))))
}

// cache is the Cache bar `width` wide: filled with the share of the cache's lifetime left, dim
// green, then yellow and red below `t`, and empty when cold; then the minutes until the cache goes
// cold, rounded up, or that it is cold, in dim red; then, with `showSize`, the cache's size, the
// tokens the next request writes again once it is cold.
func cache(c PromptCache, width int, t Thresholds, showSize bool) string {
	left := 0.0
	if c.Warm && c.ExpiresAt != nil {
		left = *c.ExpiresAt - float64(now().Unix())
	}
	pct, state := 0, paint("2;31", "cold")
	if left > 0 {
		// A TTL it doesn't know shows full.
		pct = int(math.Round(left / max(lifetimes[c.TTL], left) * 100))
		state = strconv.Itoa(int(math.Ceil(left/60))) + "m"
	}
	color := "2;32"
	switch {
	case left <= 0 || pct < t.Red:
		color = "2;31"
	case pct < t.Yellow:
		color = "2;33"
	}
	part := paint(color, blocks(pct, width)) + " " + state
	if tokens := c.RecacheTokensIfCold; showSize && tokens != nil && *tokens > 0 {
		part += " " + thousands(*tokens)
	}
	return part
}

// resetTime is "HH:MM" in local time: the 5-hour window resets within 5 hours, so the day goes
// without saying.
func resetTime(epochSeconds float64) string {
	return time.Unix(int64(epochSeconds), 0).Format("15:04")
}

// resetDay is the weekday, in local time, as "Mon": the 7-day window resets within a week, so the
// day says when.
func resetDay(epochSeconds float64) string {
	return time.Unix(int64(epochSeconds), 0).Format("Mon")
}

// right is the model and its effort when set, as "Opus 5.5 (high)".
func right(in Input) string {
	model := in.Model.DisplayName
	if model == "" {
		return ""
	}
	if effort := in.Effort.Level; effort != "" {
		model += " (" + effort + ")"
	}
	return label(model)
}

// middle is the bars of `l`, in its order, `width` wide, the 5-hour and 7-day ones with when they
// reset when `showReset`.
func (l Layout) middle(in Input, width int, showReset bool) string {
	var parts []string
	for _, name := range l.Bars {
		t := l.Thresholds[name]
		switch name {
		case "context":
			c := in.ContextWindow
			if c == nil {
				continue
			}
			// Before the first reply the context window has no percentage: it shows empty.
			used := 0.0
			if c.UsedPercentage != nil {
				used = *c.UsedPercentage
			}
			part := label("Ctx") + " " + bar(used, width, t)
			// The tokens the percentage counts, in thousands; none before the first reply.
			if c.TotalInputTokens > 0 {
				part += " " + thousands(c.TotalInputTokens)
			}
			parts = append(parts, part)
		case "cache":
			if c := in.PromptCache; c != nil && c.CachingObserved {
				// The cache's size is the context's tokens again: it shows only without them.
				showSize := !slices.Contains(l.Bars, "context")
				parts = append(parts, label("Cache")+" "+cache(*c, width, t, showSize))
			}
		case "5h":
			five := in.RateLimits.FiveHour
			if five.UsedPercentage == nil {
				continue
			}
			part := label("5h") + " " + bar(*five.UsedPercentage, width, t)
			if showReset && five.ResetsAt != nil {
				part += " " + paint("2;90", "("+resetTime(*five.ResetsAt)+")")
			}
			parts = append(parts, part)
		case "7d":
			week := in.RateLimits.SevenDay
			if week.UsedPercentage == nil {
				continue
			}
			part := label("7d") + " " + bar(*week.UsedPercentage, width, t)
			if showReset && week.ResetsAt != nil {
				part += " " + paint("2;90", "("+resetDay(*week.ResetsAt)+")")
			}
			parts = append(parts, part)
		}
	}
	return strings.Join(parts, " ")
}

var colorCodes = regexp.MustCompile(`\x1b\[[0-9;]*m`)

// visible is how many columns `s` takes, its colors left out.
func visible(s string) int { return utf8.RuneCountInString(colorCodes.ReplaceAllString(s, "")) }

// margin is the columns Claude Code keeps free beside the status line, two on each side; it cuts
// a longer one short.
const margin = 4

// Render is the Status line for a terminal `columns` wide: the branch on the left, the bars of `l`
// centered, and the model with its effort flush with the right edge. When the line is too narrow
// it shrinks the bars, then drops the reset times, then the model.
func (l Layout) Render(in Input, branch string, columns int) string {
	width := max(40, columns-margin)
	left := ""
	if branch != "" {
		left = paint("01;35", branch)
	}
	r := right(in)
	fits := func(mid string) bool {
		n := visible(left) + visible(mid) + 1
		if r != "" {
			n += visible(r) + 1
		}
		return n <= width
	}
	var mid string
	for _, stage := range []struct {
		width     int
		showReset bool
	}{{10, true}, {5, true}, {5, false}} {
		if mid = l.middle(in, stage.width, stage.showReset); fits(mid) {
			break
		}
	}
	if !fits(mid) {
		r = ""
	}
	end := width
	if r != "" {
		end = width - visible(r) - 1
	}
	start := max(min((width-visible(mid))/2, end-visible(mid)), visible(left)+1)
	line := left + strings.Repeat(" ", start-visible(left)) + mid
	if r == "" {
		return line
	}
	return line + strings.Repeat(" ", max(1, width-visible(r)-visible(line))) + r
}

// Branch is the branch checked out in `dir`, or its commit when detached; "" outside a repo.
func Branch(dir string) string {
	if dir == "" {
		return ""
	}
	git := func(args ...string) (string, error) {
		out, err := exec.Command("git", append([]string{"--no-optional-locks", "-C", dir}, args...)...).Output()
		return strings.TrimSpace(string(out)), err
	}
	name, err := git("branch", "--show-current")
	if err != nil || name != "" {
		return name
	}
	commit, _ := git("rev-parse", "--short", "HEAD")
	return commit
}
