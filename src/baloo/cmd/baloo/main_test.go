package main

import (
	"bytes"
	"testing"
)

func TestRun(t *testing.T) {
	for _, tc := range []struct {
		args         []string
		code         int
		stdout, errs string
	}{
		{[]string{"version"}, 0, "dev\n", ""},
		{nil, 2, "", "usage: baloo version\n"},
		{[]string{"nope"}, 2, "", "usage: baloo version\n"},
		{[]string{"version", "extra"}, 2, "", "usage: baloo version\n"},
	} {
		var stdout, stderr bytes.Buffer
		code := run(tc.args, &stdout, &stderr)
		if code != tc.code || stdout.String() != tc.stdout || stderr.String() != tc.errs {
			t.Errorf("run(%q) = %d, %q, %q; want %d, %q, %q",
				tc.args, code, stdout.String(), stderr.String(), tc.code, tc.stdout, tc.errs)
		}
	}
}
