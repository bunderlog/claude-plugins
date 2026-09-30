package main

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Platforms are the GOOS/GOARCH pairs the binary is built for; the loader picks its own.
var Platforms = [][2]string{
	{"darwin", "amd64"},
	{"darwin", "arm64"},
	{"linux", "amd64"},
	{"linux", "arm64"},
}

// Build builds the binary of `version` for every platform into `dir` under the repo at `root`, and
// returns their SHA256SUMS. The Go version comes from go.mod, and the other settings are fixed here
// rather than taken from the environment, so each is a static binary, without cgo, that runs on
// any machine of its platform (GOAMD64=v1, GOARM64=v8.0).
func Build(root, dir, version string) (string, error) {
	src := filepath.Join(root, names.Src)
	gomod, err := os.ReadFile(filepath.Join(src, "go.mod"))
	if err != nil {
		return "", err
	}
	goVersion := regexp.MustCompile(`(?m)^go (\S+)$`).FindSubmatch(gomod)
	if goVersion == nil {
		return "", fmt.Errorf("go.mod has no go line")
	}
	dir, err = filepath.Abs(dir)
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	var sums strings.Builder
	for _, p := range Platforms {
		name := names.Binary(version, p[0], p[1])
		out := filepath.Join(dir, name)
		cmd := exec.Command("go", "build", "-trimpath", "-buildvcs=false",
			"-ldflags", "-s -w -X main.version="+version, "-o", out, "./cmd/"+names.Plugin)
		cmd.Dir = src
		cmd.Env = append(os.Environ(),
			"GOENV=off", "GOFLAGS=", "GOEXPERIMENT=", "CGO_ENABLED=0",
			"GOTOOLCHAIN=go"+string(goVersion[1]),
			"GOOS="+p[0], "GOARCH="+p[1], "GOAMD64=v1", "GOARM64=v8.0")
		cmd.Stdout, cmd.Stderr = os.Stderr, os.Stderr
		if err := cmd.Run(); err != nil {
			return "", fmt.Errorf("building %s: %w", name, err)
		}
		data, err := os.ReadFile(out)
		if err != nil {
			return "", err
		}
		fmt.Fprintf(&sums, "%x  %s\n", sha256.Sum256(data), name)
	}
	return sums.String(), nil
}

// Version is the plugin's version, from its manifest in the repo at `root`.
func Version(root string) (string, error) {
	data, err := os.ReadFile(filepath.Join(root, names.Manifest))
	if err != nil {
		return "", err
	}
	var manifest struct{ Version string }
	if err := json.Unmarshal(data, &manifest); err != nil {
		return "", fmt.Errorf("%s: %w", names.Manifest, err)
	}
	if manifest.Version == "" {
		return "", fmt.Errorf("%s has no version", names.Manifest)
	}
	return manifest.Version, nil
}
