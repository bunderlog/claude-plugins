// Package migrations holds the database's schema as goose migrations, built into the binary, which
// runs them at start (ADR stack).
package migrations

import "embed"

// FS is every migration of this folder.
//
//go:embed *.sql
var FS embed.FS
