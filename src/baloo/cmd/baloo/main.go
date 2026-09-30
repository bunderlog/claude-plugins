// Command baloo is the plugin's binary: a subcommand for each part of the plugin.
package main

import (
	"fmt"
	"io"
	"os"
)

// version is set when a Release is built (`-X main.version=…`); a binary built from source
// says "dev".
var version = "dev"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 1 && args[0] == "version" {
		fmt.Fprintln(stdout, version)
		return 0
	}
	fmt.Fprintln(stderr, "usage: baloo version")
	return 2
}
