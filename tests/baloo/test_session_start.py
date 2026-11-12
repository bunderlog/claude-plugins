import os
import shutil
import subprocess
import unittest

from tests import testkit

# baloo's session-start script, as its SessionStart Hook runs it.
SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
    "plugins", "baloo", "scripts", "session-start",
)
INBOX = ".about/inbox.md"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class SessionStart(unittest.TestCase):
    def setUp(self):
        self.dir = testkit.repo(self)
        for key in ("BALOO_SESSION_REVIEW", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CONFIG_DIR"):
            os.environ.pop(key, None)
        os.environ["CLAUDE_PROJECT_DIR"] = self.dir

    def start(self):
        p = subprocess.run(
            ["sh", SCRIPT], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual((p.returncode, p.stderr), (0, ""))
        return p.stdout

    # Session start counts the Inbox's items, not a heading in a fenced block, and how many were
    # gone through once and kept.
    def test_inbox(self):
        tail = ": tell the user, and that /baloo:inbox goes through them\n"
        for inbox, want in [
            ("# Inbox\n\n## One\n\ntext\n### not an item\n\n## Two\n",
             ".about/inbox.md holds 2 items to consider" + tail),
            ("# Inbox\n\n## One\n\n```md\n## not an item\n```\n",
             ".about/inbox.md holds 1 item to consider" + tail),
            ("# Inbox\n", ""),
            ("# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n\n## Two\n\n2026-10-01 · adr"
             "\n\ntext · kept 2026-10-02\n",
             ".about/inbox.md holds 2 items to consider, 1 not gone through yet" + tail),
            ("# Inbox\n\n## One\n\n2026-10-01 · adr · kept 2026-10-02\n",
             ".about/inbox.md holds 1 item to consider, each gone through once and kept" + tail),
        ]:
            with self.subTest(inbox=inbox):
                write(os.path.join(self.dir, INBOX), inbox)
                testkit.git(self.dir, "add", INBOX)
                testkit.git(self.dir, "commit", "-q", "-m", "docs: inbox")
                self.assertEqual(self.start(), "baloo:\n" + want if want else "")

    # Session start names the files in .about/ with changes git hasn't committed, new ones too,
    # for the user to commit, but not the Proposals, and a headless session is shown nothing.
    def test_uncommitted_about(self):
        write(os.path.join(self.dir, ".about/glossary.md"), "# Glossary\n")
        testkit.git(self.dir, "add", ".about/glossary.md")
        testkit.git(self.dir, "commit", "-q", "-m", "docs: glossary")
        self.assertEqual(self.start(), "")

        write(os.path.join(self.dir, ".about/glossary.md"), "# Glossary\n\nchanged\n")
        write(os.path.join(self.dir, ".about/adr/new.md"), "# New\n")
        write(os.path.join(self.dir, ".about/proposals/r.md"), "# Session review r\n")
        index = ("ADRs, each .about/adr/<name>.md:\n- new: New\n"
                 "Before a task's first edit, read the ADR, PRD or Issue above that it touches, "
                 "and say where the code already breaks it\n")
        self.assertEqual(
            self.start(),
            "baloo:\n" + index + ".about/ has changes git hasn't committed: .about/adr/new.md, "
            ".about/glossary.md: tell the user, and that committing them is theirs\n",
        )
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertEqual(self.start(), "baloo:\n" + index)

    # Session start names each ADR and PRD of this repo's .about/ of 2026-11-10, its headings
    # alone, by file name and title, and each term, in under 4,500 characters (PRD index).
    def test_index(self):
        about = os.path.join(os.path.dirname(os.path.realpath(__file__)), "about-2026-11-10")
        shutil.copytree(about, os.path.join(self.dir, ".about"))
        testkit.git(self.dir, "add", ".about")
        testkit.git(self.dir, "commit", "-q", "-m", "docs: about")
        out = self.start()
        lines = out.splitlines()
        self.assertEqual(lines[0], "baloo:")
        for kind, count in [("adr", 24), ("prd", 12)]:
            names = sorted(os.listdir(os.path.join(about, kind)))
            self.assertEqual(len(names), count)
            for name in names:
                with open(os.path.join(about, kind, name), encoding="utf-8") as f:
                    title = f.readline().rstrip("\n")[2:]
                self.assertIn(f"- {name[:-3]}: {title}", lines)
        self.assertIn("- index: Session start names every decision, requirement, Issue and term "
                      "the project keeps", lines)
        terms = [line for line in lines if line.startswith("Terms in .about/glossary.md: ")]
        self.assertEqual(len(terms[0].split(", ")), 28)
        self.assertIn("Release, GitHub Release, bagheera", terms[0])
        self.assertLess(len(out) - len("baloo:\n"), 4500)

    # A new ADR, uncommitted, shows by the title of its heading, and session start writes no
    # file in the repo, HOME or Claude Code's own folder.
    def test_index_new_adr(self):
        home, own = testkit.tempdir(self), testkit.tempdir(self)
        os.environ.update({"HOME": home, "CLAUDE_CONFIG_DIR": own})
        write(os.path.join(self.dir, ".about/adr/new.md"), "Date: x\n\n# Something is decided\n")
        self.assertIn("\n- new: Something is decided\n", self.start())
        self.assertEqual(testkit.git(self.dir, "status", "--porcelain", "--untracked-files=all"),
                         "?? .about/adr/new.md\n")
        self.assertEqual((os.listdir(home), os.listdir(own)), ([], []))

    # A file with no heading outside a fenced block is named alone; a term in a fenced block
    # isn't one; a file in a subfolder isn't listed.
    def test_index_edge_cases(self):
        write(os.path.join(self.dir, ".about/adr/bare.md"), "```\n# not a title\n```\ntext\n")
        write(os.path.join(self.dir, ".about/adr/old/gone.md"), "# Gone\n")
        write(os.path.join(self.dir, ".about/issues/fix.md"), "# Fix the thing\n")
        write(os.path.join(self.dir, ".about/glossary.md"),
              "# G\n\n**One**:\nA term.\n\n```md\n**Two**:\n```\n_Avoid_: **three**\n")
        testkit.git(self.dir, "add", ".about")
        testkit.git(self.dir, "commit", "-q", "-m", "docs: about")
        self.assertEqual(
            self.start(),
            "baloo:\nADRs, each .about/adr/<name>.md:\n- bare\n"
            "Issues, each .about/issues/<name>.md:\n- fix: Fix the thing\n"
            "Terms in .about/glossary.md: One\n"
            "Before a task's first edit, read the ADR, PRD or Issue above that it touches, "
            "and say where the code already breaks it; "
            "write the glossary's terms as it uses them\n",
        )

    # A glossary alone gives its terms and the line about them; an empty .about/ gives nothing.
    def test_index_glossary_only(self):
        os.makedirs(os.path.join(self.dir, ".about/adr"))
        self.assertEqual(self.start(), "")
        write(os.path.join(self.dir, ".about/glossary.md"), "# G\n\n**One**:\n\n**Two words**:\n")
        testkit.git(self.dir, "add", ".about")
        testkit.git(self.dir, "commit", "-q", "-m", "docs: glossary")
        self.assertEqual(
            self.start(),
            "baloo:\nTerms in .about/glossary.md: One, Two words\n"
            "Write the glossary's terms as it uses them\n",
        )

    # An index past 8,000 characters is cut, says what it left out, and the Inbox and the
    # uncommitted files still show in full after it.
    def test_index_cut(self):
        for i in range(300):
            write(os.path.join(self.dir, f".about/adr/a{i:03}.md"), "# " + "x" * 80 + "\n")
        write(os.path.join(self.dir, ".about/prd/p.md"), "# P\n")
        write(os.path.join(self.dir, ".about/glossary.md"), "# G\n\n**One**:\n")
        write(os.path.join(self.dir, INBOX), "# Inbox\n\n## One\n")
        testkit.git(self.dir, "add", ".about")
        testkit.git(self.dir, "commit", "-q", "-m", "docs: about")
        write(os.path.join(self.dir, ".about/adr/z.md"), "# Z\n")
        out = self.start()
        index, inbox, uncommitted = out[len("baloo:\n"):].rsplit("\n", 3)[:3]
        self.assertLessEqual(len(index), 8000)
        lines = index.splitlines()
        shown = len([line for line in lines if line.startswith("- a") and ": " in line])
        self.assertGreater(shown, 0)
        self.assertIn(f"- and {301 - shown} more in .about/adr/", lines)
        self.assertIn("PRDs: 1 more in .about/prd/", lines)
        self.assertIn("Terms: 1 more in .about/glossary.md", lines)
        self.assertTrue(inbox.startswith(".about/inbox.md holds 1 item to consider"))
        self.assertTrue(uncommitted.startswith(
            ".about/ has changes git hasn't committed: .about/adr/z.md:"))

    # Session start says nothing outside a repo, in Claude Code's own folder, or in a Session
    # review's session.
    def test_says_nothing(self):
        write(os.path.join(self.dir, ".about/adr/new.md"), "# New\n")
        os.environ["BALOO_SESSION_REVIEW"] = "1"
        self.assertEqual(self.start(), "")
        del os.environ["BALOO_SESSION_REVIEW"]
        os.environ["CLAUDE_CONFIG_DIR"] = self.dir
        self.assertEqual(self.start(), "")
        del os.environ["CLAUDE_CONFIG_DIR"]
        os.environ["CLAUDE_PROJECT_DIR"] = testkit.tempdir(self)
        self.assertEqual(self.start(), "")


if __name__ == "__main__":
    unittest.main()
