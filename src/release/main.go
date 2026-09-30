// Command release makes a Release of the baloo plugin (ADR releases). It is not part of the
// plugin, so a change to it needs no Release. Run it in this module:
//
//	go run .        make a Release from the commits since the last one
//	go run . build  build the manifest's version for every platform into dist/
//
// dist/ is at the repo root, and a build empties it first, so it holds only the one version.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
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
		version, err := Release(root, time.Now().Format(time.DateOnly))
		if err != nil {
			return err
		}
		fmt.Printf("released %s: push it with `git push --follow-tags`\n", version)
		return nil
	case len(args) == 1 && args[0] == "build":
		version, err := Version(root)
		if err != nil {
			return err
		}
		if err := os.RemoveAll(dist); err != nil {
			return err
		}
		sums, err := Build(root, dist, version)
		if err != nil {
			return err
		}
		fmt.Print(sums)
		return os.WriteFile(filepath.Join(dist, "SHA256SUMS"), []byte(sums), 0o644)
	default:
		return fmt.Errorf("usage: go run . [build]")
	}
}
