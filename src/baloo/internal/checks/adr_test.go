package checks

import (
	"slices"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

const today = "2026-10-01"

// adr is an ADR dated `date`, a draft when `proposed`, with the decision `decision`.
func adr(date string, proposed bool, decision string) string {
	status := ""
	if proposed {
		status = "Status: proposed\n"
	}
	return "# Billing\n\n" + status + "Date: " + date + "\n\n" + decision + "\n"
}

// adrRepo is a repo with the accepted ADR billing.md dated 2026-09-30, and the draft draft.md,
// committed.
func adrRepo(t *testing.T) string {
	t.Helper()
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{
		".about/adr/billing.md": adr("2026-09-30", false, "Invoices are monthly."),
		".about/adr/draft.md":   adr("2026-09-30", true, "Invoices may be weekly."),
	})
	testkit.Git(t, dir, "commit", "-q", "-m", "docs: adr")
	return dir
}

func noStaleADRDate(t *testing.T, dir string) []string {
	t.Helper()
	found, err := NoStaleADRDate(dir, today)
	if err != nil {
		t.Fatalf("NoStaleADRDate: %v", err)
	}
	return found
}

func TestNoStaleADRDate_FindsAnADRChangedUnderAnOldDate(t *testing.T) {
	dir := adrRepo(t)
	stage(t, dir, map[string]string{".about/adr/billing.md": adr("2026-09-30", false, "Invoices are weekly.")})
	want := []string{".about/adr/billing.md: changed, but its Date is 2026-09-30; set it to " + today}
	if got := noStaleADRDate(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoStaleADRDate = %q, want %q", got, want)
	}
}

// An ADR changed again on the day of its Date passes as well.
func TestNoStaleADRDate_PassesAnADRDatedToday(t *testing.T) {
	dir := adrRepo(t)
	stage(t, dir, map[string]string{".about/adr/billing.md": adr(today, false, "Invoices are weekly.")})
	if got := noStaleADRDate(t, dir); got != nil {
		t.Errorf("NoStaleADRDate = %q, want none", got)
	}
	testkit.Git(t, dir, "commit", "-q", "-m", "docs: weekly")
	stage(t, dir, map[string]string{".about/adr/billing.md": adr(today, false, "Invoices are daily.")})
	if got := noStaleADRDate(t, dir); got != nil {
		t.Errorf("NoStaleADRDate changed again today = %q, want none", got)
	}
}

// Accepting a draft changes it: it takes today's Date.
func TestNoStaleADRDate_FindsADraftAcceptedUnderAnOldDate(t *testing.T) {
	dir := adrRepo(t)
	stage(t, dir, map[string]string{".about/adr/draft.md": adr("2026-09-30", false, "Invoices may be weekly.")})
	want := []string{".about/adr/draft.md: changed, but its Date is 2026-09-30; set it to " + today}
	if got := noStaleADRDate(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoStaleADRDate = %q, want %q", got, want)
	}
}

func TestNoStaleADRDate_FindsAnADRWithoutADate(t *testing.T) {
	dir := adrRepo(t)
	stage(t, dir, map[string]string{".about/adr/billing.md": "# Billing\n\nInvoices are weekly.\n"})
	want := []string{".about/adr/billing.md: has no Date line; add Date: " + today + " under its title"}
	if got := noStaleADRDate(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoStaleADRDate = %q, want %q", got, want)
	}
}

// A draft, a new ADR, a deleted or renamed one, and a file beside the ADRs pass.
func TestNoStaleADRDate_PassesWhatIsNotAChangedADR(t *testing.T) {
	dir := adrRepo(t)
	stage(t, dir, map[string]string{
		".about/adr/draft.md":  adr("2026-09-30", true, "Invoices may be daily."),
		".about/adr/tax.md":    adr("2026-09-30", false, "Prices include tax."),
		".about/adr/notes.txt": "Date: 2026-09-30\n",
		".about/glossary.md":   "Date: 2026-09-30\n",
		"docs/adr/billing.md":  adr("2026-09-30", false, "Elsewhere."),
	})
	if got := noStaleADRDate(t, dir); got != nil {
		t.Errorf("NoStaleADRDate = %q, want none", got)
	}
	testkit.Git(t, dir, "commit", "-q", "-m", "docs: more")
	testkit.Git(t, dir, "mv", ".about/adr/billing.md", ".about/adr/invoices.md")
	testkit.Git(t, dir, "rm", "-q", ".about/adr/tax.md")
	if got := noStaleADRDate(t, dir); got != nil {
		t.Errorf("NoStaleADRDate after a rename and a deletion = %q, want none", got)
	}
}

func TestNoStaleADRDate_FailsOutsideARepo(t *testing.T) {
	if _, err := NoStaleADRDate(t.TempDir(), today); err == nil {
		t.Error("NoStaleADRDate outside a repo = no error, want one")
	}
}
