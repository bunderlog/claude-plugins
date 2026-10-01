package checks

import (
	"strings"
	"testing"
)

func TestConventionalCommit_Accepts(t *testing.T) {
	for _, message := range []string{
		"feat: add login",
		"fix(adr): correct a date",
		"feat!: drop node",
		"refactor(api/auth)!: split parse\n\nBody.",
		"feat: x\n\nBreaking change: a body line, not a footer.\n\nRefs: #1",
		"feat(multi word): a scope with spaces",
		"fix(ZrOpticsTab): a scope in any case",
		"docs: explain `README` and the API",
		"feat: 2 new checks",
		"feat: " + strings.Repeat("x", 94),
		"fix: x\n\n" + strings.Repeat("y", 100),
		"feat: é" + strings.Repeat("x", 93),
		"feat: x\n# ------------------------ >8 ------------------------\n" + strings.Repeat("z", 200),
		"# Please enter the commit message\n\ndocs: explain config",
		"Merge branch 'main' into feature",
		`Revert "feat: add login"`,
		`Reapply "feat: add login"`,
		"Merge pull request #7 from a/b",
		"Merge remote-tracking branch 'origin/main'",
		"fixup! feat: add login",
		"squash! feat: add login",
		"feat: x\n# a comment\n\nBody.",
		"feat: x\n# ------------------------ >8 ------------------------\ndiff --git a b",
		"feat: x\n\nBody.\n\nBREAKING CHANGE: drops node",
		"feat: x\n\nBREAKING-CHANGE: drops node\nRefs: #12",
		"feat: x\n\nBreaking change: not a token, so a body line",
		"feat: x\n\nRefs: #1\nbreaking change: part of the Refs value",
		"feat: x\n\nReviewed-by: Z\nCloses #42",
		"",
	} {
		if got := ConventionalCommit(message, CommitRules{}); got != "" {
			t.Errorf("ConventionalCommit(%q) = %q, want none", message, got)
		}
	}
}

// The examples in the Conventional Commits 1.0.0 specification, with LF and with CRLF.
func TestConventionalCommit_AcceptsTheSpecsExamples(t *testing.T) {
	for _, message := range []string{
		"feat: allow provided config object to extend other configs\n\nBREAKING CHANGE: `extends` " +
			"key in config file is now used for extending other config files",
		"feat!: send an email to the customer when a product is shipped",
		"feat(api)!: send an email to the customer when a product is shipped",
		"feat!: drop support for Node 6\n\nBREAKING CHANGE: use JavaScript features not available " +
			"in Node 6.",
		"docs: correct spelling of CHANGELOG",
		"feat(lang): add Polish language",
		"fix: prevent racing of requests\n\nIntroduce a request id and a reference to latest " +
			"request. Dismiss\nincoming responses other than from latest request.\n\nRemove " +
			"timeouts which were used to mitigate the racing issue but are\nobsolete now.\n\n" +
			"Reviewed-by: Z\nRefs: #123",
		"revert: let us never again speak of the noodle incident\n\nRefs: 676104e, a215868",
	} {
		crlf := strings.ReplaceAll(message, "\n", "\r\n") + "\r\n"
		for _, m := range []string{message, crlf} {
			if got := ConventionalCommit(m, CommitRules{}); got != "" {
				t.Errorf("ConventionalCommit(%q) = %q, want none", m, got)
			}
		}
	}
}

func TestConventionalCommit_RejectsASubjectOfAnotherShape(t *testing.T) {
	for _, message := range []string{"add login", "fix bug: x", "feat:add login", "feat:  x",
		"feat(): x", "feat( ): x", "feat (a): x", "feat: ", "Merge sort for the index"} {
		want := `"` + message + `" is not ` + "`type(scope): description`"
		if got := ConventionalCommit(message, CommitRules{}); got != want {
			t.Errorf("ConventionalCommit(%q) = %q, want %q", message, got, want)
		}
	}
}

// commitlint's config-conventional error rules.
func TestConventionalCommit_RejectsWhatCommitlintDoes(t *testing.T) {
	for _, tc := range []struct{ message, want string }{
		{"wip: any type", `"wip" is not one of build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test`},
		{"i18n: digits in the type", `"i18n" is not one of build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test`},
		{"Feat: any case", `"Feat" is not one of build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test`},
		{"fix: Add Thing", `"Add Thing" starts with an uppercase letter`},
		{"fix: API timeout", `"API timeout" starts with an uppercase letter`},
		{"fix: add thing.", `"add thing." ends with a full stop`},
		{"fix: add thing ", `"fix: add thing " has trailing spaces`},
		{"feat: x\nBody.", `leave a blank line between "feat: x" and the body`},
		{"feat: " + strings.Repeat("x", 95), `"feat: ` + strings.Repeat("x", 34) + `…" is 101 characters, over 100`},
		{"fix: x\n\n" + strings.Repeat("y", 101), `"` + strings.Repeat("y", 40) + `…" is 101 characters, over 100`},
		{"fix: x\n\nRefs: " + strings.Repeat("1", 100), `"Refs: ` + strings.Repeat("1", 34) + `…" is 106 characters, over 100`},
	} {
		if got := ConventionalCommit(tc.message, CommitRules{}); got != tc.want {
			t.Errorf("ConventionalCommit(%q) = %q, want %q", tc.message, got, tc.want)
		}
	}
}

func TestConventionalCommit_RejectsABreakingChangeFooterOfAnotherShape(t *testing.T) {
	for _, footer := range []string{"Breaking-Change: x", "breaking-change: x", "BREAKING CHANGE #12",
		"BREAKING-CHANGE #12"} {
		want := `"` + footer + `" is not ` + "`BREAKING CHANGE: description`"
		if got := ConventionalCommit("feat: x\n\nRefs: #1\n"+footer, CommitRules{}); got != want {
			t.Errorf("ConventionalCommit with the footer %q = %q, want %q", footer, got, want)
		}
	}
	// Footers are the trailing paragraphs that open with one, across blank lines.
	want := `"breaking-change: y" is not ` + "`BREAKING CHANGE: description`"
	if got := ConventionalCommit("feat: x\n\nBody.\n\nbreaking-change: y\n\nRefs: #1", CommitRules{}); got != want {
		t.Errorf("ConventionalCommit with a footer two paragraphs up = %q, want %q", got, want)
	}
}

func TestConventionalCommit_TakesItsOwnTypesOrAny(t *testing.T) {
	own := CommitRules{Types: []string{"wip", "feat"}}
	for _, tc := range []struct {
		message string
		rules   CommitRules
		want    string
	}{
		{"wip: x", own, ""},
		{"fix: x", own, `"fix" is not one of wip, feat`},
		{"wip: x", CommitRules{AnyType: true}, ""},
		{"add x", CommitRules{AnyType: true}, `"add x" is not ` + "`type(scope): description`"},
	} {
		if got := ConventionalCommit(tc.message, tc.rules); got != tc.want {
			t.Errorf("ConventionalCommit(%q, %+v) = %q, want %q", tc.message, tc.rules, got, tc.want)
		}
	}
}

func TestConventionalCommit_TakesItsOwnLineLengthOrNone(t *testing.T) {
	max72, none := 72, 0
	for _, tc := range []struct {
		message string
		max     *int
		want    string
	}{
		{"feat: " + strings.Repeat("x", 67), &max72, `"feat: ` + strings.Repeat("x", 34) + `…" is 73 characters, over 72`},
		{"feat: x\n\n" + strings.Repeat("y", 73), &max72, `"` + strings.Repeat("y", 40) + `…" is 73 characters, over 72`},
		{"feat: " + strings.Repeat("x", 500), &none, ""},
	} {
		if got := ConventionalCommit(tc.message, CommitRules{MaxLength: tc.max}); got != tc.want {
			t.Errorf("ConventionalCommit(%q) with the limit %d = %q, want %q", tc.message, *tc.max, got, tc.want)
		}
	}
}
