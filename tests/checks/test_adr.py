import unittest

from baloo.checks import Error, no_stale_adr_date
from tests import testkit
from tests.checks import stage

TODAY = "2026-10-01"


def adr(date: str, decision: str) -> str:
    """An ADR dated `date` with the decision `decision`."""
    return f"# Billing\n\nDate: {date}\n\n{decision}\n"


class NoStaleADRDate(unittest.TestCase):
    def setUp(self):
        """A repo with the ADR billing.md dated 2026-09-30, committed."""
        self.dir = testkit.repo(self)
        stage(self.dir, {".about/adr/billing.md": adr("2026-09-30", "Invoices are monthly.")})
        testkit.git(self.dir, "commit", "-q", "-m", "docs: adr")

    def found(self):
        return no_stale_adr_date(self.dir, TODAY)

    def test_finds_an_adr_changed_under_an_old_date(self):
        stage(self.dir, {".about/adr/billing.md": adr("2026-09-30", "Invoices are weekly.")})
        self.assertEqual(
            self.found(),
            [".about/adr/billing.md: changed, but its Date is 2026-09-30; set it to 2026-10-01"],
        )

    # An ADR with CRLF line endings is read as with LF.
    def test_reads_crlf(self):
        stage(
            self.dir,
            {".about/adr/billing.md": f"# Billing\r\n\r\nDate: {TODAY}\r\n\r\nWeekly.\r\n"},
        )
        self.assertEqual(self.found(), [])

    # An ADR changed again on the day of its Date passes as well.
    def test_passes_an_adr_dated_today(self):
        stage(self.dir, {".about/adr/billing.md": adr(TODAY, "Invoices are weekly.")})
        self.assertEqual(self.found(), [])
        testkit.git(self.dir, "commit", "-q", "-m", "docs: weekly")
        stage(self.dir, {".about/adr/billing.md": adr(TODAY, "Invoices are daily.")})
        self.assertEqual(self.found(), [])

    def test_finds_an_adr_without_a_date(self):
        stage(self.dir, {".about/adr/billing.md": "# Billing\n\nInvoices are weekly.\n"})
        self.assertEqual(
            self.found(),
            [".about/adr/billing.md: has no Date line; add Date: 2026-10-01 under its title"],
        )

    # A new ADR, a deleted or renamed one, and a file beside the ADRs pass.
    def test_passes_what_is_not_a_changed_adr(self):
        stage(
            self.dir,
            {
                ".about/adr/tax.md": adr("2026-09-30", "Prices include tax."),
                ".about/adr/notes.txt": "Date: 2026-09-30\n",
                ".about/glossary.md": "Date: 2026-09-30\n",
                "docs/adr/billing.md": adr("2026-09-30", "Elsewhere."),
            },
        )
        self.assertEqual(self.found(), [])
        testkit.git(self.dir, "commit", "-q", "-m", "docs: more")
        testkit.git(self.dir, "mv", ".about/adr/billing.md", ".about/adr/invoices.md")
        testkit.git(self.dir, "rm", "-q", ".about/adr/tax.md")
        self.assertEqual(self.found(), [])

    def test_fails_outside_a_repo(self):
        with self.assertRaises(Error):
            no_stale_adr_date(testkit.tempdir(self), TODAY)


if __name__ == "__main__":
    unittest.main()
