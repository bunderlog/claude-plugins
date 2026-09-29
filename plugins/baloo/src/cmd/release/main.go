// Command release makes a Release of the baloo plugin (ADR releases). Run it in this module:
//
//	go run ./cmd/release        make a Release from the commits since the last one
//	go run ./cmd/release build  build the manifest's version for every platform into dist/
//
// dist/ is at the repo root.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/bunderlog/claude-plugins/plugins/baloo/src/internal/release"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintf(os.Stderr, "release: %v\n", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	out, err := exec.Command("git", "rev-parse", "--show-toplevel").Output()
	if err != nil {
		return fmt.Errorf("not in the repo: %w", err)
	}
	root := strings.TrimSpace(string(out))
	dist := filepath.Join(root, "dist")
	switch {
	case len(args) == 0:
		version, err := release.Release(root, dist, time.Now().Format(time.DateOnly))
		if err != nil {
			return err
		}
		fmt.Printf("released %s: push it with `git push --follow-tags`\n", version)
		return nil
	case len(args) == 1 && args[0] == "build":
		version, err := release.Version(root)
		if err != nil {
			return err
		}
		sums, err := release.Build(root, dist, version)
		if err != nil {
			return err
		}
		fmt.Print(sums)
		return os.WriteFile(filepath.Join(dist, "SHA256SUMS"), []byte(sums), 0o644)
	default:
		return fmt.Errorf("usage: go run ./cmd/release [build]")
	}
}
