package main

import "testing"

func TestNext(t *testing.T) {
	fix := Commit{"a1", "fix: a fix"}
	feat := Commit{"b2", "feat(status-line): a feature"}
	bang := Commit{"c3", "refactor!: a breaking change"}
	footer := Commit{"d4", "chore: tidy\n\nBREAKING CHANGE: the config moved"}
	docs := Commit{"e5", "docs: words"}
	for _, tc := range []struct {
		version string
		commits []Commit
		changed bool
		want    string
	}{
		{"0.3.1", []Commit{fix}, false, ""},
		{"0.3.1", []Commit{docs}, true, "0.3.2"},
		{"0.3.1", []Commit{fix}, true, "0.3.2"},
		{"0.3.1", []Commit{fix, feat}, true, "0.4.0"},
		{"0.3.1", []Commit{bang}, true, "0.4.0"},
		{"0.3.1", []Commit{footer}, true, "0.4.0"},
		{"1.3.1", []Commit{feat}, true, "1.4.0"},
		{"1.3.1", []Commit{feat, bang}, true, "2.0.0"},
		{"0.0.0", []Commit{feat}, true, "0.1.0"},
	} {
		got, err := Next(tc.version, tc.commits, tc.changed)
		if err != nil || got != tc.want {
			t.Errorf("Next(%s, %v, %v) = %q, %v; want %q", tc.version, tc.commits, tc.changed, got, err, tc.want)
		}
	}
	if _, err := Next("1.2", nil, true); err == nil {
		t.Error("Next(1.2) took a version without a patch")
	}
}

func TestSection(t *testing.T) {
	commits := []Commit{
		{"a1", "fix: a fix"},
		{"b2", "feat(status-line): a feature\n\nwith a body"},
		{"c3", "docs: words"},
		{"d4", "feat!: a breaking feature"},
	}
	want := `## 0.4.0 — 2026-09-29

### Breaking changes

- a breaking feature (d4)

### Features

- status-line: a feature (b2)

### Fixes

- a fix (a1)
`
	if got := Section("0.4.0", "2026-09-29", commits); got != want {
		t.Errorf("Section() =\n%s\nwant\n%s", got, want)
	}
	want = "## 0.4.1 — 2026-09-29\n\nNo feature changes or fixes.\n"
	if got := Section("0.4.1", "2026-09-29", commits[2:3]); got != want {
		t.Errorf("Section(docs only) = %q; want %q", got, want)
	}
}

// The README's CI recipe pins the new version; nothing else in it changes.
func TestPin(t *testing.T) {
	readme := "Pin it:\n\n```sh\nset -e\nversion=0.9.0\nfile=baloo_${version}_linux_amd64\n```\n\nversion=0.9.0 in prose.\n"
	want := "Pin it:\n\n```sh\nset -e\nversion=0.10.0\nfile=baloo_${version}_linux_amd64\n```\n\nversion=0.9.0 in prose.\n"
	if got, err := Pin([]byte(readme), "0.10.0"); string(got) != want || err != nil {
		t.Errorf("Pin = %q, %v; want %q", got, err, want)
	}
}

// A README with no line to pin, or more than one, is an error rather than a Release that leaves
// the recipe behind.
func TestPin_NotOneLine(t *testing.T) {
	for _, readme := range []string{"no recipe\n", "  version=0.9.0\n", "version=0.9.0\r\n",
		"version=0.9.0\nversion=0.9.0\n"} {
		if _, err := Pin([]byte(readme), "0.10.0"); err == nil {
			t.Errorf("Pin(%q) = nil error; want one", readme)
		}
	}
}
