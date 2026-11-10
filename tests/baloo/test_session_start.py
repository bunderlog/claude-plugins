import os
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
        self.assertEqual(
            self.start(),
            "baloo:\n.about/ has changes git hasn't committed: .about/adr/new.md, "
            ".about/glossary.md: tell the user, and that committing them is theirs\n",
        )
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertEqual(self.start(), "")

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
