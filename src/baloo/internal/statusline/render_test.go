package statusline

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"
	"testing"
	"time"
)

// plain is `s` without its colors.
func plain(s string) string { return colorCodes.ReplaceAllString(s, "") }

// input is the Input Claude Code gives as the JSON `text`.
func input(t *testing.T, text string) Input {
	t.Helper()
	var in Input
	if err := json.Unmarshal([]byte(text), &in); err != nil {
		t.Fatal(err)
	}
	return in
}

// at is the epoch seconds of a local time on 2026-09-24, or the day after for a `day` of 25.
func at(day, hour, minute int) int64 {
	return time.Date(2026, 9, day, hour, minute, 0, 0, time.Local).Unix()
}

func TestBar(t *testing.T) {
	th := thresholds{50, 80}
	for _, tc := range []struct {
		percent float64
		width   int
		want    string
	}{
		{34.6, 10, "███░░░░░░░ 35%"},
		{150, 5, "█████ 100%"},
		{-3, 5, "░░░░░ 0%"},
	} {
		if got := plain(bar(tc.percent, tc.width, th)); got != tc.want {
			t.Errorf("bar(%v, %d) = %q; want %q", tc.percent, tc.width, got, tc.want)
		}
	}
	for percent, color := range map[float64]string{49: "\x1b[2;32m", 50: "\x1b[2;33m", 80: "\x1b[2;31m"} {
		if got := bar(percent, 10, th); !strings.HasPrefix(got, color) {
			t.Errorf("bar(%v) = %q; want it to start %q", percent, got, color)
		}
	}
}

// The context bar is yellow from 15% and red from 20%.
func TestRender_ContextColors(t *testing.T) {
	for used, color := range map[string]string{
		"14.4": "\x1b[2;32m", "15": "\x1b[2;33m", "19.4": "\x1b[2;33m", "20": "\x1b[2;31m",
	} {
		got := Render(input(t, `{"context_window": {"used_percentage": `+used+`}}`), "", 120)
		if !strings.Contains(got, color) {
			t.Errorf("context at %s%% = %q; want %q in it", used, got, color)
		}
	}
}

// The reset time shows alone, even past midnight.
func TestResetTime(t *testing.T) {
	if got := resetTime(float64(at(24, 14, 5))); got != "14:05" {
		t.Errorf("resetTime = %q; want 14:05", got)
	}
	if got := resetTime(float64(at(25, 1, 0))); got != "01:00" {
		t.Errorf("resetTime past midnight = %q; want 01:00", got)
	}
}

// usage is an Input with every Usage bar, and `extra` fields.
func usage(t *testing.T, extra string) Input {
	t.Helper()
	return input(t, fmt.Sprintf(`{"context_window": {"used_percentage": 12}, "rate_limits": {
		"five_hour": {"used_percentage": 55, "resets_at": %d},
		"seven_day": {"used_percentage": 81}}%s}`, at(24, 14, 0), extra))
}

const model = `, "model": {"display_name": "Opus 5.5"}, "effort": {"level": "high"}`

func TestRender_Layout(t *testing.T) {
	line := plain(Render(usage(t, ""), "main", 200))
	if !strings.HasPrefix(line, "main ") || !strings.Contains(line, "Ctx █░░░░░░░░░ 12% 5h █████░░░░░ 55% (") ||
		!strings.HasSuffix(line, "7d ████████░░ 81%") {
		t.Errorf("line = %q; want the branch on the left, then the bars", line)
	}
	mid := len([]rune(line)) - strings.Index(line, "Ctx")
	if got, want := len([]rune(line[:strings.Index(line, "Ctx")])), (196-mid)/2; got != want {
		t.Errorf("bars start at %d; want %d, centered", got, want)
	}

	colored := Render(usage(t, model), "main", 200)
	line = plain(colored)
	if !regexp.MustCompile(`81% {2,}Opus 5\.5 \(high\)$`).MatchString(line) || len([]rune(line)) != 196 {
		t.Errorf("line = %q (%d wide); want the model flush right in 196", line, len([]rune(line)))
	}
	// The effort shares the model's color.
	if !strings.HasSuffix(colored, "\x1b[2;37mOpus 5.5 (high)\x1b[00m") {
		t.Errorf("line = %q; want the model and effort in one color", colored)
	}
	if got := plain(Render(input(t, `{"model": {"display_name": "Opus 5.5"}}`), "", 120)); !strings.HasSuffix(got, " Opus 5.5") {
		t.Errorf("model alone = %q; want it on the right", got)
	}
}

// When narrow, the line shrinks the bars, then drops the reset time, then the model.
func TestRender_Narrow(t *testing.T) {
	in := usage(t, model)
	for _, tc := range []struct {
		columns int
		want    string
		suffix  bool
	}{
		{87, "Ctx █░░░░░░░░░ 12%", false},
		{86, "Ctx ░░░░░ 12% 5h ██░░░ 55% (", false},
		{72, "55% (", false},
		{71, "55% 7d ████░ 81% Opus 5.5 (high)", false},
		{64, "Opus 5.5 (high)", true},
		{63, "7d ████░ 81%", true},
	} {
		line := plain(Render(in, "main", tc.columns))
		if tc.suffix && !strings.HasSuffix(line, tc.want) || !tc.suffix && !strings.Contains(line, tc.want) {
			t.Errorf("%d columns: %q; want %q in it", tc.columns, line, tc.want)
		}
	}
}

// The bars never overlap the branch, and the line shows nothing it isn't given.
func TestRender_Bounds(t *testing.T) {
	if got := plain(Render(usage(t, ""), "a-very-long-branch-name-that-fills-the-line", 20)); !strings.Contains(got, "line Ctx") {
		t.Errorf("long branch = %q; want the bars after it", got)
	}
	if got := Render(Input{}, "", 120); strings.TrimSpace(got) != "" {
		t.Errorf("nothing given = %q; want a blank line", got)
	}
	if got := visible(Render(usage(t, ""), "", 120)); got > 116 {
		t.Errorf("line is %d wide; want at most 116", got)
	}
}

// Before the first reply the context bar shows empty.
func TestRender_EmptyContext(t *testing.T) {
	for _, window := range []string{`{}`, `{"used_percentage": null}`, `{"used_percentage": 0, "total_input_tokens": 0}`} {
		got := strings.TrimSpace(plain(Render(input(t, `{"context_window": `+window+`}`), "", 120)))
		if got != "Ctx ░░░░░░░░░░ 0%" {
			t.Errorf("context %s = %q; want an empty bar", window, got)
		}
	}
}

// The context's tokens follow its percentage, rounded to thousands.
func TestRender_Tokens(t *testing.T) {
	for tokens, want := range map[string]string{"120400": "60% (120K)", "199600": "60% (200K)", "400": "60% (0K)"} {
		got := plain(Render(input(t, `{"context_window": {"used_percentage": 60, "total_input_tokens": `+tokens+`}}`), "", 120))
		if !strings.HasSuffix(got, want) {
			t.Errorf("%s tokens = %q; want it to end %q", tokens, got, want)
		}
	}
}

func TestBranch(t *testing.T) {
	t.Setenv("GIT_CONFIG_GLOBAL", os.DevNull)
	t.Setenv("GIT_CONFIG_NOSYSTEM", "1")
	dir := t.TempDir()
	if got := Branch(dir); got != "" {
		t.Skipf("the temporary folder is inside a repo, on %q", got)
	}
	git := func(args ...string) string {
		out, err := exec.Command("git", append([]string{"-C", dir}, args...)...).Output()
		if err != nil {
			t.Fatalf("git %v: %v", args, err)
		}
		return strings.TrimSpace(string(out))
	}
	git("init", "-q", "-b", "work")
	if got := Branch(dir); got != "work" {
		t.Errorf("Branch = %q; want work, not yet with a commit", got)
	}
	git("-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
		"commit", "-q", "--allow-empty", "-m", "x")
	git("checkout", "-q", "--detach")
	if got, want := Branch(dir), git("rev-parse", "--short", "HEAD"); got != want {
		t.Errorf("Branch detached = %q; want the commit %q", got, want)
	}
	if got := Branch(""); got != "" {
		t.Errorf("Branch without a folder = %q; want none", got)
	}
}
