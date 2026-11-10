package db

import (
	"context"
	"strings"
	"testing"
	"time"
)

func TestOpen_NamesTheStepThatFailed(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	for _, tc := range []struct {
		name, url, want string
	}{
		{"a URL that doesn't parse", "postgres://x@127.0.0.1:notaport/x", "connect to the database: "},
		{"a server that isn't there", "postgres://x@127.0.0.1:1/x?connect_timeout=2", "migrate the database: "},
	} {
		t.Run(tc.name, func(t *testing.T) {
			pool, err := Open(ctx, tc.url)
			if err == nil {
				pool.Close()
				t.Fatalf("Open(%q) = nil error, want one starting %q", tc.url, tc.want)
			}
			if !strings.HasPrefix(err.Error(), tc.want) {
				t.Fatalf("Open(%q) error = %q, want it to start %q", tc.url, err, tc.want)
			}
		})
	}
}
