package statusline

import (
	"fmt"
	"math"
	"os/exec"
	"regexp"
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
	RateLimits struct {
		FiveHour Limit `json:"five_hour"`
		SevenDay Limit `json:"seven_day"`
	} `json:"rate_limits"`
}

// Limit is one of the rate limits; a field Claude Code doesn't give is nil.
type Limit struct {
	UsedPercentage *float64 `json:"used_percentage"`
	ResetsAt       *float64 `json:"resets_at"`
}

// thresholds are the percentages from which a Usage bar turns yellow and red.
type thresholds struct{ yellow, red int }

var (
	contextBar  = thresholds{15, 20}
	fiveHourBar = thresholds{70, 85}
	sevenDayBar = thresholds{80, 95}
)

const reset = "\x1b[00m"

func paint(code, text string) string { return "\x1b[" + code + "m" + text + reset }
func label(text string) string       { return paint("2;37", text) }

// bar is a Usage bar `width` wide and its percentage: dim green, yellow and red from `t`.
func bar(percent float64, width int, t thresholds) string {
	pct := int(min(100, max(0, math.Round(percent))))
	filled := pct * width / 100
	color := "2;32"
	switch {
	case pct >= t.red:
		color = "2;31"
	case pct >= t.yellow:
		color = "2;33"
	}
	return paint(color, strings.Repeat("█", filled)+strings.Repeat("░", width-filled)) +
		" " + strconv.Itoa(pct) + "%"
}

// resetTime is "HH:MM" in local time: the 5-hour window resets within 5 hours, so the day goes
// without saying.
func resetTime(epochSeconds float64) string {
	return time.Unix(int64(epochSeconds), 0).Format("15:04")
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

// middle is the Usage bars `width` wide, the 5-hour one with its reset time when `showReset`.
func middle(in Input, width int, showReset bool) string {
	var parts []string
	if c := in.ContextWindow; c != nil {
		// Before the first reply the context window has no percentage: it shows empty.
		used := 0.0
		if c.UsedPercentage != nil {
			used = *c.UsedPercentage
		}
		part := label("Ctx") + " " + bar(used, width, contextBar)
		// The tokens the percentage counts, in thousands; none before the first reply.
		if c.TotalInputTokens > 0 {
			part += " " + paint("2;90", fmt.Sprintf("(%dK)", int(math.Round(c.TotalInputTokens/1000))))
		}
		parts = append(parts, part)
	}
	if five := in.RateLimits.FiveHour; five.UsedPercentage != nil {
		part := label("5h") + " " + bar(*five.UsedPercentage, width, fiveHourBar)
		if showReset && five.ResetsAt != nil {
			part += " " + paint("2;90", "("+resetTime(*five.ResetsAt)+")")
		}
		parts = append(parts, part)
	}
	if week := in.RateLimits.SevenDay.UsedPercentage; week != nil {
		parts = append(parts, label("7d")+" "+bar(*week, width, sevenDayBar))
	}
	return strings.Join(parts, " ")
}

var colorCodes = regexp.MustCompile(`\x1b\[[0-9;]*m`)

// visible is how many columns `s` takes, its colors left out.
func visible(s string) int { return utf8.RuneCountInString(colorCodes.ReplaceAllString(s, "")) }

// margin is the columns Claude Code keeps free beside the status line, two on each side; it cuts
// a longer one short.
const margin = 4

// Render is the Status line for a terminal `columns` wide: the branch on the left, the Usage bars
// centered, and the model with its effort flush with the right edge. When the line is too narrow
// it shrinks the bars, then drops the 5-hour reset time, then the model.
func Render(in Input, branch string, columns int) string {
	width := max(40, columns-margin)
	l := ""
	if branch != "" {
		l = paint("01;35", branch)
	}
	r := right(in)
	fits := func(mid string) bool {
		n := visible(l) + visible(mid) + 1
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
		if mid = middle(in, stage.width, stage.showReset); fits(mid) {
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
	start := max(min((width-visible(mid))/2, end-visible(mid)), visible(l)+1)
	line := l + strings.Repeat(" ", start-visible(l)) + mid
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
