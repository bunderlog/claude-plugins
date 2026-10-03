// Package loader_test runs the plugin's Loader, scripts/loader, as a Hook would: a process with an
// explicit environment, downloading from a local server in place of the GitHub Release.
package loader_test

import (
	"crypto/sha256"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"slices"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

const version = "1.2.3"

// loader is a copy of the plugin's Loader beside a manifest of `version`, a Release of that
// version served with this machine's binary and a SHA256SUMS, and a plugin data folder to
// download into.
type loader struct {
	script, data, file string
	sums               string // the Release's SHA256SUMS; none is served while it is ""
	downloads          atomic.Int32
	server             *httptest.Server
}

func setup(t *testing.T, binary []byte) *loader {
	t.Helper()
	dir := t.TempDir()
	l := &loader{
		script: filepath.Join(dir, "scripts", "loader"),
		data:   filepath.Join(dir, "data"),
		file:   names.Binary(version, runtime.GOOS, runtime.GOARCH),
	}
	src, err := os.ReadFile("../../../../" + names.PluginDir + "/scripts/loader")
	if err != nil {
		t.Fatal(err)
	}
	for _, f := range []struct {
		path string
		data []byte
	}{
		{l.script, src},
		{filepath.Join(dir, ".claude-plugin", "plugin.json"), []byte(`{"name": "baloo", "version": "` + version + `"}`)},
	} {
		if err := os.MkdirAll(filepath.Dir(f.path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(f.path, f.data, 0o755); err != nil {
			t.Fatal(err)
		}
	}
	l.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v" + version + "/" + l.file:
			l.downloads.Add(1)
			w.Write(binary)
		case "/v" + version + "/SHA256SUMS":
			if l.sums == "" {
				http.NotFound(w, r)
				return
			}
			w.Write([]byte(l.sums))
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(l.server.Close)
	return l
}

// files lists the plugin data folder.
func (l *loader) files() []string {
	entries, _ := os.ReadDir(l.data)
	var names []string
	for _, e := range entries {
		names = append(names, e.Name())
	}
	return names
}

// withSum makes the Release's SHA256SUMS list `sum` for this machine's binary, among binaries for
// other platforms.
func (l *loader) withSum(sum string) {
	other := strings.Repeat("0", 64)
	l.sums = fmt.Sprintf("%s  %s\n%s  %s\n%s  %s\n", other, names.Binary(version, "plan9", "mips"),
		sum, l.file, other, names.Binary(version, "aix", "ppc64"))
}

func (l *loader) run(t *testing.T, env []string, args ...string) (stdout, stderr string, code int) {
	t.Helper()
	return l.runWith(t, "", env, args...)
}

// runWith runs the Loader as run does, with `stdin` for its standard input.
func (l *loader) runWith(t *testing.T, stdin string, env []string, args ...string) (stdout, stderr string, code int) {
	t.Helper()
	cmd := exec.Command("sh", append([]string{l.script}, args...)...)
	cmd.Stdin = strings.NewReader(stdin)
	cmd.Env = append([]string{
		"PATH=/usr/bin:/bin",
		"HOME=" + t.TempDir(),
		"BALOO_RELEASES=" + l.server.URL,
		"CLAUDE_PLUGIN_DATA=" + l.data,
	}, env...)
	var out, errs strings.Builder
	cmd.Stdout, cmd.Stderr = &out, &errs
	err := cmd.Run()
	code = cmd.ProcessState.ExitCode()
	if err != nil && code < 0 {
		t.Fatal(err)
	}
	return out.String(), errs.String(), code
}

// binary builds cmd/baloo for this machine as `version`.
func binary(t *testing.T) []byte {
	t.Helper()
	out := filepath.Join(t.TempDir(), "baloo")
	build := exec.Command("go", "build", "-ldflags", "-X main.version="+version, "-o", out, "../../cmd/baloo")
	if b, err := build.CombinedOutput(); err != nil {
		t.Fatalf("go build: %v\n%s", err, b)
	}
	data, err := os.ReadFile(out)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestLoader(t *testing.T) {
	bin := binary(t)
	sum := fmt.Sprintf("%x", sha256.Sum256(bin))

	t.Run("downloads the binary once and runs it", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		if out, errs, code := l.run(t, nil, "version"); code != 2 || out != "" ||
			!strings.Contains(errs, l.file+" is not downloaded") {
			t.Errorf("version before install = %d, %q, %q", code, out, errs)
		}
		for range 2 {
			if out, errs, code := l.run(t, nil, "install"); code != 0 || out != "" || errs != "" {
				t.Fatalf("install = %d, %q, %q", code, out, errs)
			}
		}
		if n := l.downloads.Load(); n != 1 {
			t.Errorf("install downloaded the binary %d times; want once", n)
		}
		if out, errs, code := l.run(t, nil, "version"); code != 0 || out != version+"\n" || errs != "" {
			t.Errorf("version = %d, %q, %q; want 0, %q", code, out, errs, version+"\n")
		}
		if got, want := l.files(), []string{l.file, l.file + ".sha256"}; !slices.Equal(got, want) {
			t.Errorf("data folder holds %q; want %q", got, want)
		}
	})

	t.Run("session-start downloads the binary, then runs it", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		project := t.TempDir()
		if err := os.MkdirAll(filepath.Join(project, ".git"), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.MkdirAll(filepath.Join(project, ".claude"), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(project, names.Config), []byte("nope: 1\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		out, errs, code := l.run(t, []string{"CLAUDE_PROJECT_DIR=" + project}, "session-start")
		if code != 0 || !strings.Contains(out, "nope is not a setting") || errs != "" {
			t.Errorf("session-start = %d, %q, %q; want 0 and the config's problem", code, out, errs)
		}
		if n := l.downloads.Load(); n != 1 {
			t.Errorf("session-start downloaded the binary %d times; want once", n)
		}
		if got, want := l.files(), []string{l.file, l.file + ".sha256"}; !slices.Equal(got, want) {
			t.Errorf("data folder holds %q after session-start; want %q", got, want)
		}
	})

	t.Run("deletes other versions a week after their last use", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		// Found at a later session start, with this version's binary there already.
		stale := names.Binary("0.9.0", runtime.GOOS, runtime.GOARCH)
		recent := names.Binary("1.0.0", runtime.GOOS, runtime.GOARCH)
		for name, age := range map[string]time.Duration{stale: 30 * 24 * time.Hour, recent: 24 * time.Hour} {
			path := filepath.Join(l.data, name)
			if err := os.WriteFile(path, []byte("old"), 0o755); err != nil {
				t.Fatal(err)
			}
			then := time.Now().Add(-age)
			if err := os.Chtimes(path, then, then); err != nil {
				t.Fatal(err)
			}
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		if got, want := l.files(), []string{recent, l.file, l.file + ".sha256"}; !slices.Equal(got, want) ||
			l.downloads.Load() != 1 {
			t.Errorf("data folder holds %q after %d downloads; want %q after one", got, l.downloads.Load(), want)
		}
	})

	t.Run("running the binary counts as using it", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		path := filepath.Join(l.data, l.file)
		// The Hooks that never fail count too: a session longer than a week runs only them.
		for _, sub := range []string{"version", "pre-tool-use", "post-tool-use", "session-end", "user-prompt-submit", "stop", "subagent-start"} {
			then := time.Now().Add(-30 * 24 * time.Hour)
			if err := os.Chtimes(path, then, then); err != nil {
				t.Fatal(err)
			}
			l.runWith(t, "{}", nil, sub)
			if info, err := os.Stat(path); err != nil || time.Since(info.ModTime()) > time.Hour {
				t.Errorf("binary last modified %v after a run of %s; want now", info.ModTime(), sub)
			}
		}
	})

	t.Run("downloads a damaged binary again", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte("#!/bin/sh\necho damaged\n"), 0o755); err != nil {
			t.Fatal(err)
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 || errs != "" {
			t.Fatalf("install over a damaged binary = %d, %q", code, errs)
		}
		if out, _, _ := l.run(t, nil, "version"); out != version+"\n" || l.downloads.Load() != 2 {
			t.Errorf("version = %q after %d downloads; want %q after two", out, l.downloads.Load(), version+"\n")
		}
	})

	t.Run("without sha256sum or shasum stops before downloading", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		// A PATH of every tool the Loader runs but those two.
		tools := t.TempDir()
		for _, tool := range []string{
			"dirname", "uname", "sed", "head", "cat", "cut", "find", "mkdir", "touch", "curl", "awk", "rm",
			"chmod", "mv",
		} {
			path, err := exec.LookPath(tool)
			if err != nil {
				t.Skipf("no %s: %v", tool, err)
			}
			if err := os.Symlink(path, filepath.Join(tools, tool)); err != nil {
				t.Fatal(err)
			}
		}
		_, errs, code := l.run(t, []string{"PATH=" + tools}, "install")
		if code != 2 || strings.Count(errs, "needs sha256sum or shasum") != 1 || l.downloads.Load() != 1 {
			t.Errorf("install = %d, %q after %d downloads; want 2 and the one message after one",
				code, errs, l.downloads.Load())
		}
	})

	t.Run("matches the binary's name exactly in SHA256SUMS", func(t *testing.T) {
		l := setup(t, bin)
		// Its dots are not wildcards: a name that differs only there is another binary's.
		lookalike := strings.ReplaceAll(l.file, ".", "x")
		l.sums = sum + "  " + lookalike + "\n"
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "no binary for "+runtime.GOOS+"/"+runtime.GOARCH) {
			t.Errorf("install = %d, %q; want 2 and no binary for this platform", code, errs)
		}
	})

	t.Run("refuses a binary whose sha256 differs", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(strings.Repeat("a", 64))
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "not the "+strings.Repeat("a", 64)) {
			t.Errorf("install = %d, %q; want 2 and the sha256 mismatch", code, errs)
		}
		if entries, _ := os.ReadDir(l.data); len(entries) != 0 {
			t.Errorf("data folder holds %v after a refused download; want nothing", entries)
		}
	})

	t.Run("says why a download fails", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		_, errs, code := l.run(t, []string{"BALOO_RELEASES=" + l.server.URL + "/missing"}, "install")
		if code != 2 || !strings.Contains(errs, "could not download "+l.server.URL+"/missing/v"+version+"/SHA256SUMS") {
			t.Errorf("install = %d, %q; want 2 and the URL", code, errs)
		}
		if entries, _ := os.ReadDir(l.data); len(entries) != 0 {
			t.Errorf("data folder holds %v after a failed download; want nothing", entries)
		}
	})

	t.Run("needs the Release's SHA256SUMS", func(t *testing.T) {
		l := setup(t, bin)
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "could not download "+l.server.URL+"/v"+version+"/SHA256SUMS") {
			t.Errorf("install = %d, %q; want 2 and the SHA256SUMS URL", code, errs)
		}
		if n := l.downloads.Load(); n != 0 {
			t.Errorf("install downloaded the binary %d times without a SHA256SUMS; want never", n)
		}
	})

	t.Run("needs a binary for this platform", func(t *testing.T) {
		l := setup(t, bin)
		l.sums = strings.Repeat("0", 64) + "  " + names.Binary(version, "plan9", "mips") + "\n"
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "no binary for "+runtime.GOOS+"/"+runtime.GOARCH) {
			t.Errorf("install = %d, %q; want 2 and no binary for this platform", code, errs)
		}
	})

	t.Run("allow-guideline never stops a Read", func(t *testing.T) {
		read := `{"tool_name": "Read", "tool_input": {"file_path": "/plugin/guidelines/go.md"}}`
		l := setup(t, bin)
		l.withSum(sum)
		for _, env := range [][]string{nil, {"CLAUDE_PLUGIN_DATA="}} {
			if out, errs, code := l.runWith(t, read, env, "allow-guideline"); code != 0 || out != "" || errs != "" {
				t.Errorf("allow-guideline with %q, no binary = %d, %q, %q; want 0 and nothing", env, code, out, errs)
			}
		}
		if n := l.downloads.Load(); n != 0 {
			t.Errorf("allow-guideline downloaded the binary %d times; want never", n)
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		// A binary without allow-guideline, as an older version is, fails: the Loader says nothing.
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte("#!/bin/sh\necho usage >&2\nexit 2\n"), 0o755); err != nil {
			t.Fatal(err)
		}
		if out, errs, code := l.runWith(t, read, nil, "allow-guideline"); code != 0 || out != "" || errs != "" {
			t.Errorf("allow-guideline with a binary that fails = %d, %q, %q; want 0 and nothing", code, out, errs)
		}
		// The binary gets the call as the Loader got it; one of another file never reaches it.
		stdin := filepath.Join(t.TempDir(), "stdin")
		script := "#!/bin/sh\ncat >" + stdin + "\n"
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte(script), 0o755); err != nil {
			t.Fatal(err)
		}
		l.runWith(t, `{"file_path": "/elsewhere/a.md"}`, nil, "allow-guideline")
		if _, err := os.Stat(stdin); err == nil {
			t.Errorf("allow-guideline ran the binary for a Read of another file")
		}
		l.runWith(t, read, nil, "allow-guideline")
		if got, _ := os.ReadFile(stdin); string(got) != read+"\n" {
			t.Errorf("the binary got %q; want %q", got, read+"\n")
		}
	})

	t.Run("session-end never fails the exit", func(t *testing.T) {
		end := `{"transcript_path": "/t.jsonl"}`
		l := setup(t, bin)
		l.withSum(sum)
		if out, errs, code := l.runWith(t, end, nil, "session-end"); code != 0 || out != "" || errs != "" {
			t.Errorf("session-end, no binary = %d, %q, %q; want 0 and nothing", code, out, errs)
		}
		if n := l.downloads.Load(); n != 0 {
			t.Errorf("session-end downloaded the binary %d times; want never", n)
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		stdin := filepath.Join(t.TempDir(), "stdin")
		script := "#!/bin/sh\ncat > " + stdin + "\necho usage >&2\nexit 2\n"
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte(script), 0o755); err != nil {
			t.Fatal(err)
		}
		if out, errs, code := l.runWith(t, end, nil, "session-end"); code != 0 || out != "" || errs != "" {
			t.Errorf("session-end with a binary that fails = %d, %q, %q; want 0 and nothing", code, out, errs)
		}
		if got, _ := os.ReadFile(stdin); string(got) != end+"\n" {
			t.Errorf("the binary got %q; want %q", got, end+"\n")
		}
	})

	t.Run("pre-tool-use never stops a tool call it can't check", func(t *testing.T) {
		call := `{"tool_name": "Bash", "tool_input": {"command": "git status"}}`
		l := setup(t, bin)
		l.withSum(sum)
		if out, errs, code := l.runWith(t, call, nil, "pre-tool-use"); code != 0 || out != "" || errs != "" {
			t.Errorf("pre-tool-use, no binary = %d, %q, %q; want 0 and nothing", code, out, errs)
		}
		if n := l.downloads.Load(); n != 0 {
			t.Errorf("pre-tool-use downloaded the binary %d times; want never", n)
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 {
			t.Fatalf("install = %d, %q", code, errs)
		}
		// A binary of an older version, without pre-tool-use, fails: the Loader says nothing.
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte("#!/bin/sh\necho usage >&2\nexit 2\n"), 0o755); err != nil {
			t.Fatal(err)
		}
		if out, errs, code := l.runWith(t, call, nil, "pre-tool-use"); code != 0 || out != "" || errs != "" {
			t.Errorf("pre-tool-use with a binary that fails = %d, %q, %q; want 0 and nothing", code, out, errs)
		}
		// The binary gets every call, and what it prints reaches Claude Code.
		script := "#!/bin/sh\ncat\n"
		if err := os.WriteFile(filepath.Join(l.data, l.file), []byte(script), 0o755); err != nil {
			t.Fatal(err)
		}
		if out, _, code := l.runWith(t, call, nil, "pre-tool-use"); code != 0 || out != call+"\n" {
			t.Errorf("pre-tool-use = %d, %q; want 0 and the binary's %q", code, out, call+"\n")
		}
	})

	t.Run("the hooks after a prompt, an edit, a turn and a subagent's start never block", func(t *testing.T) {
		turn := `{"session_id": "s1"}`
		for _, hook := range []string{"user-prompt-submit", "stop", "post-tool-use", "subagent-start"} {
			l := setup(t, bin)
			l.withSum(sum)
			if hook == "user-prompt-submit" {
				// It downloads a missing binary, so a Release it can't download is what it meets.
				l.sums = ""
			}
			if out, errs, code := l.runWith(t, turn, nil, hook); code != 0 || out != "" || errs != "" {
				t.Errorf("%s, no binary = %d, %q, %q; want 0 and nothing", hook, code, out, errs)
			}
			if n := l.downloads.Load(); n != 0 {
				t.Errorf("%s downloaded the binary %d times; want never", hook, n)
			}
			l.withSum(sum)
			if _, errs, code := l.run(t, nil, "install"); code != 0 {
				t.Fatalf("install = %d, %q", code, errs)
			}
			// A binary of an older version, without the subcommand, fails: the Loader says nothing.
			if err := os.WriteFile(filepath.Join(l.data, l.file), []byte("#!/bin/sh\necho usage >&2\nexit 2\n"), 0o755); err != nil {
				t.Fatal(err)
			}
			if out, errs, code := l.runWith(t, turn, nil, hook); code != 0 || out != "" || errs != "" {
				t.Errorf("%s with a binary that fails = %d, %q, %q; want 0 and nothing", hook, code, out, errs)
			}
			// What the binary prints, such as the Stop check's block, reaches Claude Code.
			if err := os.WriteFile(filepath.Join(l.data, l.file), []byte("#!/bin/sh\ncat\n"), 0o755); err != nil {
				t.Fatal(err)
			}
			if out, _, code := l.runWith(t, turn, nil, hook); code != 0 || out != turn+"\n" {
				t.Errorf("%s = %d, %q; want 0 and the binary's %q", hook, code, out, turn+"\n")
			}
		}
	})

	t.Run("user-prompt-submit downloads a missing binary and runs its session start", func(t *testing.T) {
		// A session the plugin was updated in: its Hooks are the new version's, which no
		// SessionStart Hook downloaded.
		l := setup(t, bin)
		l.withSum(sum)
		project := t.TempDir()
		for _, dir := range []string{".git", ".claude"} {
			if err := os.MkdirAll(filepath.Join(project, dir), 0o755); err != nil {
				t.Fatal(err)
			}
		}
		if err := os.WriteFile(filepath.Join(project, names.Config), []byte("nope: 1\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		env := []string{"CLAUDE_PROJECT_DIR=" + project}
		out, errs, code := l.runWith(t, `{"session_id": "s1"}`, env, "user-prompt-submit")
		if code != 0 || errs != "" || !strings.Contains(out, `"hookEventName":"UserPromptSubmit"`) ||
			!strings.Contains(out, "nope is not a setting") {
			t.Errorf("user-prompt-submit, no binary = %d, %q, %q; want 0 and session start's JSON for "+
				"UserPromptSubmit", code, out, errs)
		}
		// Once it is there, a prompt runs only the binary's user-prompt-submit.
		out, errs, code = l.runWith(t, `{"session_id": "s1"}`, env, "user-prompt-submit")
		if code != 0 || out != "" || errs != "" || l.downloads.Load() != 1 {
			t.Errorf("second user-prompt-submit = %d, %q, %q after %d downloads; want 0 and nothing after one",
				code, out, errs, l.downloads.Load())
		}
	})

	t.Run("needs the plugin data folder", func(t *testing.T) {
		l := setup(t, bin)
		l.withSum(sum)
		_, errs, code := l.run(t, []string{"CLAUDE_PLUGIN_DATA="}, "install")
		if code != 2 || !strings.Contains(errs, "CLAUDE_PLUGIN_DATA is not set") {
			t.Errorf("install = %d, %q; want 2 and CLAUDE_PLUGIN_DATA", code, errs)
		}
	})
}
