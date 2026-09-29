// Package loader_test runs the plugin's loader, scripts/baloo, as a hook would: a process with an
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
	"strings"
	"sync/atomic"
	"testing"

	"github.com/bunderlog/claude-plugins/plugins/baloo/src/internal/names"
)

const version = "1.2.3"

// loader is a copy of the plugin's scripts folder with its own SHA256SUMS, a build of this
// machine's binary served at a Release URL, and a plugin data folder to download it into.
type loader struct {
	script, sums, data, build string
	requests                  atomic.Int32
	server                    *httptest.Server
}

func setup(t *testing.T, binary []byte) *loader {
	t.Helper()
	dir := t.TempDir()
	l := &loader{
		script: filepath.Join(dir, "scripts", "baloo"),
		sums:   filepath.Join(dir, "scripts", "SHA256SUMS"),
		data:   filepath.Join(dir, "data"),
		build:  names.Build(version, runtime.GOOS, runtime.GOARCH),
	}
	src, err := os.ReadFile("../../../scripts/baloo")
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Dir(l.script), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(l.script, src, 0o755); err != nil {
		t.Fatal(err)
	}
	l.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		l.requests.Add(1)
		if r.URL.Path != "/v"+version+"/"+l.build {
			http.NotFound(w, r)
			return
		}
		w.Write(binary)
	}))
	t.Cleanup(l.server.Close)
	return l
}

// writeSums lists `sum` for this machine's build, among builds for other platforms.
func (l *loader) writeSums(t *testing.T, sum string) {
	t.Helper()
	other := strings.Repeat("0", 64)
	text := fmt.Sprintf("%s  %s\n%s  %s\n%s  %s\n", other, names.Build(version, "plan9", "mips"),
		sum, l.build, other, names.Build(version, "aix", "ppc64"))
	if err := os.WriteFile(l.sums, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func (l *loader) run(t *testing.T, env []string, args ...string) (stdout, stderr string, code int) {
	t.Helper()
	cmd := exec.Command("sh", append([]string{l.script}, args...)...)
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

// binary builds cmd/baloo for this machine as the given version.
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

	t.Run("downloads the build once and runs it", func(t *testing.T) {
		l := setup(t, bin)
		l.writeSums(t, sum)
		if out, errs, code := l.run(t, nil, "version"); code != 2 || out != "" ||
			!strings.Contains(errs, l.build+" is not downloaded") {
			t.Errorf("version before install = %d, %q, %q", code, out, errs)
		}
		for range 2 {
			if out, errs, code := l.run(t, nil, "install"); code != 0 || out != "" || errs != "" {
				t.Fatalf("install = %d, %q, %q", code, out, errs)
			}
		}
		if n := l.requests.Load(); n != 1 {
			t.Errorf("install downloaded %d times; want once", n)
		}
		if out, errs, code := l.run(t, nil, "version"); code != 0 || out != version+"\n" || errs != "" {
			t.Errorf("version = %d, %q, %q; want 0, %q", code, out, errs, version+"\n")
		}
		entries, _ := os.ReadDir(l.data)
		if len(entries) != 1 || entries[0].Name() != l.build {
			t.Errorf("data folder holds %v; want only %s", entries, l.build)
		}
	})

	t.Run("downloads a damaged build again", func(t *testing.T) {
		l := setup(t, bin)
		l.writeSums(t, sum)
		if err := os.MkdirAll(l.data, 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(l.data, l.build), []byte("#!/bin/sh\necho damaged\n"), 0o755); err != nil {
			t.Fatal(err)
		}
		if _, errs, code := l.run(t, nil, "install"); code != 0 || errs != "" {
			t.Fatalf("install = %d, %q", code, errs)
		}
		if out, _, _ := l.run(t, nil, "version"); out != version+"\n" || l.requests.Load() != 1 {
			t.Errorf("version = %q after %d downloads; want %q after one", out, l.requests.Load(), version+"\n")
		}
	})

	t.Run("refuses a build whose sha256 differs", func(t *testing.T) {
		l := setup(t, bin)
		l.writeSums(t, strings.Repeat("a", 64))
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
		l.writeSums(t, sum)
		_, errs, code := l.run(t, []string{"BALOO_RELEASES=" + l.server.URL + "/missing"}, "install")
		if code != 2 || !strings.Contains(errs, "could not download "+l.server.URL+"/missing/v"+version+"/"+l.build) {
			t.Errorf("install = %d, %q; want 2 and the URL", code, errs)
		}
		if entries, _ := os.ReadDir(l.data); len(entries) != 0 {
			t.Errorf("data folder holds %v after a failed download; want nothing", entries)
		}
	})

	t.Run("needs a Release", func(t *testing.T) {
		l := setup(t, bin)
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "the plugin has no Release yet") {
			t.Errorf("install = %d, %q; want 2 and no Release yet", code, errs)
		}
	})

	t.Run("needs a build for this platform", func(t *testing.T) {
		l := setup(t, bin)
		other := strings.Repeat("0", 64) + "  " + names.Build(version, "plan9", "mips") + "\n"
		if err := os.WriteFile(l.sums, []byte(other), 0o644); err != nil {
			t.Fatal(err)
		}
		_, errs, code := l.run(t, nil, "install")
		if code != 2 || !strings.Contains(errs, "no build for "+runtime.GOOS+"/"+runtime.GOARCH) {
			t.Errorf("install = %d, %q; want 2 and no build for this platform", code, errs)
		}
	})

	t.Run("needs the plugin data folder", func(t *testing.T) {
		l := setup(t, bin)
		l.writeSums(t, sum)
		_, errs, code := l.run(t, []string{"CLAUDE_PLUGIN_DATA="}, "install")
		if code != 2 || !strings.Contains(errs, "CLAUDE_PLUGIN_DATA is not set") {
			t.Errorf("install = %d, %q; want 2 and CLAUDE_PLUGIN_DATA", code, errs)
		}
	})
}
