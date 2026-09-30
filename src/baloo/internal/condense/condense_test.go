package condense

// cspell:ignore AKIA IOSFODNN MIIE

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

// transcript is a Transcript of the lines `lines`, each a JSON object as Claude Code writes it.
func transcript(lines ...string) []byte {
	return []byte(strings.Join(lines, "\n") + "\n")
}

const (
	start  = `{"type":"user","cwd":"/repo","entrypoint":"cli","timestamp":"2026-10-01T09:00:00.000Z","message":{"role":"user","content":"add a retro skill to the plugin"}}`
	title  = `{"type":"ai-title","aiTitle":"Port retro"}`
	reply  = `{"type":"assistant","timestamp":"2026-10-01T09:01:00.000Z","message":{"role":"assistant","content":[{"type":"text","text":"On it."},{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"go test ./..."}}]}}`
	failed = `{"type":"user","timestamp":"2026-10-01T09:02:00.000Z","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","is_error":true,"content":"Exit code 1\n--- FAIL: TestX\nFAIL\tpkg"}]}}`
	passed = `{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t2","content":"ok"}]}}`
	meta   = `{"type":"user","isMeta":true,"message":{"role":"user","content":"<local-command-caveat>Caveat</local-command-caveat>"}}`
	skill  = `{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Base directory for this skill: /x\n\n# Retro"}]}}`
	remind = `{"type":"user","message":{"role":"user","content":"<system-reminder>be brief</system-reminder>"}}`
	stop   = `{"type":"user","timestamp":"2026-10-01T09:10:00.000Z","message":{"role":"user","content":[{"type":"text","text":"[Request interrupted by user]"}]}}`
	cmd    = `{"type":"user","message":{"role":"user","content":"<command-name>/baloo:ask</command-name>\n<command-message>baloo:ask</command-message>\n<command-args>port retro</command-args>"}}`
)

func TestReport_ShowsTheSessionsPromptsCommandsInterruptsAndFailures(t *testing.T) {
	s := Condense(transcript(start, title, reply, failed, passed, meta, skill, remind, stop, cmd), "abc")
	want := "# Session abc: Port retro\n" +
		"2026-10-01 09:00, 10 min, 1 tool calls, 1 failed\n" +
		"Tools: Bash 1\n" +
		"\n" +
		"[1] prompt: add a retro skill to the plugin\n" +
		"[4] error exit Bash(go test ./...): Exit code 1: --- FAIL: TestX FAIL pkg\n" +
		"[9] interrupt\n" +
		"[10] command: /baloo:ask port retro"
	if got := s.Report(); got != want {
		t.Errorf("Report =\n%s\nwant\n%s", got, want)
	}
}

// Anything that may be a Secret is masked: a kind no-secrets-in-commits knows, however short, a
// private key's whole block, and a long run of letters and digits mixed. Hex (a commit, a
// session's id), words and file names stay.
func TestMask_MasksWhatMayBeASecret(t *testing.T) {
	for _, tc := range []struct{ in, want string }{
		{"key AKIA" + "IOSFODNN7EXAMPLE here", "key ***** here"},
		{"token ghp_" + strings.Repeat("a1", 18), "token *****"},
		{"-----BEGIN RSA " + "PRIVATE KEY-----\nMIIE\nabc\n-----END RSA PRIVATE KEY-----\nafter", "*****\nafter"},
		{"x=" + strings.Repeat("Xy1", 11) + ";", "x=*****;"},
		{"commit " + strings.Repeat("0123456789abcdef", 3), "commit " + strings.Repeat("0123456789abcdef", 3)},
		{"session 2551f813-9deb-4dea-8805-3a385154298a", "session 2551f813-9deb-4dea-8805-3a385154298a"},
		{"TestLoader_without_shasum_or_sha_stops_before_downloading", "TestLoader_without_shasum_or_sha_stops_before_downloading"},
		{"src/baloo/internal/condense/condense_test.go", "src/baloo/internal/condense/condense_test.go"},
	} {
		if got := Mask(tc.in); got != tc.want {
			t.Errorf("Mask(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestReport_MasksSecrets(t *testing.T) {
	prompt := `{"type":"user","message":{"role":"user","content":"use sk-ant-` + strings.Repeat("api03-", 4) + ` for it"}}`
	if got := Condense(transcript(prompt), "abc").Report(); !strings.Contains(got, "[1] prompt: use ***** for it") {
		t.Errorf("Report =\n%s\nwant the key masked", got)
	}
}

// failure is a Transcript of one Bash call of `command` that failed with `error`.
func failure(command, error string) []byte {
	use, _ := json.Marshal(map[string]any{"type": "assistant", "message": map[string]any{
		"content": []any{map[string]any{"type": "tool_use", "id": "t1", "name": "Bash",
			"input": map[string]any{"command": command}}}}})
	result, _ := json.Marshal(map[string]any{"type": "user", "message": map[string]any{
		"content": []any{map[string]any{"type": "tool_result", "tool_use_id": "t1", "is_error": true,
			"content": error}}}})
	return transcript(string(use), string(result))
}

// A failed call's kind comes from its error, as Claude Code words it: a denial by one of the
// plugin's Checks shows which one.
func TestReport_NamesTheKindOfEachFailure(t *testing.T) {
	for _, tc := range []struct{ error, want string }{
		{"PreToolUse:Bash hook error: baloo:no-git-hook-bypass: git commit --no-verify bypasses the Git hooks.",
			"[2] error check Bash(x): PreToolUse:Bash hook error: baloo:no-git-hook-bypass: git commit --no-verify bypasses the Git hooks."},
		{"The user doesn't want to proceed with this tool use.", "[2] error rejected Bash(x): The user doesn't want to proceed with this tool use."},
		{"PreToolUse:Bash hook error: Blocked", "[2] error hook Bash(x): PreToolUse:Bash hook error: Blocked"},
		{"Permission for this action was denied by the Claude Code auto mode classifier.", "[2] error classifier Bash(x): Permission for this action was denied by the Claude Code auto mode classifier."},
		{"This command requires approval", "[2] error permission Bash(x): This command requires approval"},
		{"<tool_use_error>File has not been read yet.</tool_use_error>", "[2] error stale Bash(x): <tool_use_error>File has not been read yet.</tool_use_error>"},
		{"Exit code 2\n" + strings.Repeat("x", 250), "[2] error exit Bash(x): Exit code 2: …" + strings.Repeat("x", 200)},
		{"MCP error -1: Failed", "[2] error other Bash(x): MCP error -1: Failed"},
	} {
		got := Condense(failure("x", tc.error), "abc").Report()
		if !strings.Contains(got, "\n"+tc.want) {
			t.Errorf("Report of a call that failed with %q =\n%s\nwant the line %q", tc.error, got, tc.want)
		}
	}
}

// A call made three times or more shows Claude hunting for the same thing.
func TestReport_ShowsRepeatedCalls(t *testing.T) {
	var ls []string
	for i, path := range []string{"/repo/a.go", "/repo/a.go", "/repo/b.go", "/repo/a.go"} {
		ls = append(ls, fmt.Sprintf(`{"type":"assistant","cwd":"/repo","message":{"content":[{"type":"tool_use","id":"r%d","name":"Read","input":{"file_path":%q}}]}}`, i, path))
	}
	got := Condense(transcript(ls...), "abc").Report()
	if !strings.HasSuffix(got, "\n\nRepeated calls:\n3× Read(a.go)") {
		t.Errorf("Report =\n%s\nwant it to end with 3× Read(a.go)", got)
	}
}

// Across sessions: failures by kind, the commonest kind first, each with its commonest failures
// (a failed command by its tool, others by their error), then the prompts typed more than once.
func TestSummary_CountsFailuresByKindAndRepeatedPrompts(t *testing.T) {
	prompt := func(text string) string {
		return `{"type":"user","message":{"role":"user","content":"` + text + `"}}`
	}
	exit := failure("go test ./...", "Exit code 1\nFAIL")
	one := Condense(append(exit, transcript(prompt("run the checks and commit it"), prompt("yes"))...), "one")
	two := Condense(append(append(exit, failure("rm x", "This command requires approval")...),
		transcript(prompt("Run the checks and commit it"), prompt("yes"))...), "two")
	want := "# Across 2 sessions\n" +
		"exit: 2\n" +
		"  2× in 2 session(s): Bash\n" +
		"permission: 1\n" +
		"  1× in 1 session(s): This command requires approval\n" +
		"repeated prompts:\n" +
		"  2× run the checks and commit it"
	if got := Summary([]Session{one, two}); got != want {
		t.Errorf("Summary =\n%s\nwant\n%s", got, want)
	}
}

// Around shows a moment's lines in full, text, calls and results, each cut to 2000 characters,
// and masked: what a Retro reads instead of the raw Transcript.
func TestAround_ShowsTheLinesAroundAMomentMasked(t *testing.T) {
	long := `{"type":"assistant","message":{"content":[{"type":"text","text":"` + strings.Repeat("y", 2100) + `"}]}}`
	leak := `{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t9","content":"AWS=AKIA` + `IOSFODNN7EXAMPLE"}]}}`
	tr := transcript(start, reply, failed, long, leak, stop, cmd)
	want := "[1] user: add a retro skill to the plugin\n" +
		"[2] assistant: On it.\n" +
		"[2] assistant calls Bash(go test ./...)\n" +
		"[3] user result (failed): Exit code 1\n--- FAIL: TestX\nFAIL\tpkg\n" +
		"[4] assistant: " + strings.Repeat("y", 2000) + "\n" +
		"[5] user result: AWS=*****"
	if got := Around(tr, 3, 2); got != want {
		t.Errorf("Around(3, 2) =\n%s\nwant\n%s", got, want)
	}
}

// A Session review reads only what the user and Claude wrote, masked: no tool call or result, and
// nothing Claude Code wrote in the user's turn but a command.
func TestConversation_IsWhatTheUserAndClaudeWroteMasked(t *testing.T) {
	leak := `{"type":"assistant","message":{"content":[{"type":"text","text":"Use AKIA` + `IOSFODNN7EXAMPLE."}]}}`
	got := Conversation(transcript(start, title, reply, failed, passed, meta, skill, remind, stop, cmd, leak), 1000)
	want := "user: add a retro skill to the plugin\n\n" +
		"assistant: On it.\n\n" +
		"user: /baloo:ask port retro\n\n" +
		"assistant: Use *****."
	if got != want {
		t.Errorf("Conversation =\n%s\nwant\n%s", got, want)
	}
	if got := Conversation(transcript(start, reply), 10); got != "nt: On it." {
		t.Errorf("Conversation of at most 10 characters = %q, want its last 10", got)
	}
}
