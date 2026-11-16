"""louie's PostToolUse Hook names the ADRs and PRDs a file concerns when Claude first works on it
(PRD index)."""

import json
import os
import unittest

from tests.louie import commands
from tests.louie.commands import in_repo, run, write

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

A = ".about/adr/a.md: A is decided"
B = ".about/prd/b.md"
# What starts the Hook's naming of ADRs and PRDs, whatever Guidelines come with it.
NAMING = "ADRs and PRDs that name"


class Hook(unittest.TestCase):
    def setUp(self):
        self.dir = in_repo(self)
        write(os.path.join(self.dir, ".about/adr/a.md"),
              "# A is decided\n\nCharging lives in `src/pay/charge.go`.\n")
        write(os.path.join(self.dir, ".about/prd/b.md"),
              "# B is required\n\nPayments are `src/pay`.\n")

    def call(self, tool, file, session="s1", **fields):
        """What the Hook adds to Claude's context for `tool` on `file`, from the repo's root unless
        it is absolute; "" for nothing."""
        stdin = json.dumps({
            "session_id": session, "tool_name": tool,
            "tool_input": {"file_path": os.path.join(self.dir, file)}, **fields,
        })
        code, out, err = run("post-tool-use", stdin=stdin)
        self.assertEqual((code, err), (0, ""))
        if not out:
            return ""
        hook = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hook["hookEventName"], "PostToolUse")
        return hook["additionalContext"]

    def assertNamesNone(self, tool, file, **fields):
        self.assertNotIn(NAMING, self.call(tool, file, **fields))


class Names(Hook):
    def test_names_once_a_session(self):
        got = self.call("Read", "src/pay/charge.go")
        self.assertIn(A, got)
        self.assertIn(B + ": B is required", got)
        self.assertLess(got.index(A), got.index(B))
        self.assertIn(NAMING, got)
        self.assertIn("read them before you edit", got)
        self.assertNamesNone("Read", "src/pay/refund.go")
        self.assertNamesNone("Edit", "src/pay/refund.go")
        got = self.call("Read", "src/pay/charge.go", session="s2")
        self.assertIn(A, got)
        self.assertIn(B, got)

    def test_names_nothing_where_none_is_due(self):
        # An ADR that names the files under `.about/`, so only their being the project's knowledge
        # keeps them from being named.
        write(os.path.join(self.dir, ".about/adr/k.md"),
              "# K\n\n`.about/adr/c.md` and `.claude/worktrees/x/.about/prd/b.md`\n")
        for tool, file in [
            ("Edit", "README.md"),
            ("Write", ".about/adr/c.md"),
            ("Edit", ".claude/worktrees/x/.about/prd/b.md"),
            ("Edit", os.path.join(commands.outside_repo(self), "src/pay/charge.go")),
        ]:
            with self.subTest(file=file):
                self.assertNamesNone(tool, file)
        self.call("Read", ".about/adr/a.md", session="s2")
        self.call("Read", ".about/prd/b.md", session="s2")
        self.assertNamesNone("Read", "src/pay/charge.go", session="s2")

    def test_a_subagent_names_and_marks_nothing(self):
        self.assertNamesNone("Read", "src/pay/charge.go", agent_id="ag1")
        got = self.call("Read", "src/pay/charge.go")
        self.assertIn(A, got)
        self.assertIn(B, got)
        self.call("Read", ".about/adr/a.md", session="s2", agent_id="ag1")
        got = self.call("Read", "src/pay/charge.go", session="s2")
        self.assertIn(A, got)
        self.assertIn(B, got)

    def test_comes_with_the_guidelines(self):
        write(os.path.join(self.dir, "go.mod"), "module x\n")
        stdin = json.dumps({
            "session_id": "s1", "tool_name": "Read",
            "tool_input": {"file_path": os.path.join(self.dir, "src/pay/charge.go")},
        })
        code, out, err = run("post-tool-use", stdin=stdin)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(out.splitlines()), 1)
        got = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("The go Guideline applies to src/pay/charge.go", got)
        self.assertIn(A, got)
        self.assertIn(B, got)

    def test_a_write_that_creates_a_file(self):
        got = self.call("Write", "src/pay/new.go", tool_response={"type": "create"})
        self.assertIn(B, got)
        self.assertNotIn(A, got)

    def test_names_five_then_the_rest(self):
        for n in range(1, 7):
            write(os.path.join(self.dir, f".about/adr/x{n}.md"), f"# X{n}\n\n`src/pay/charge.go`\n")
        os.remove(os.path.join(self.dir, ".about/adr/a.md"))
        got = self.call("Read", "src/pay/charge.go")
        named = [line for line in got.splitlines() if line.startswith(".about/")]
        self.assertEqual(named, [f".about/adr/x{n}.md: X{n}" for n in range(1, 6)])
        self.assertIn("2 more name it, in .about/adr/ and .about/prd/", got)
        got = self.call("Edit", "src/pay/charge.go")
        named = [line for line in got.splitlines() if line.startswith(".about/")]
        self.assertEqual(named, [".about/adr/x6.md: X6", B + ": B is required"])
        self.assertNotIn("more name it", got)

    def test_names_nothing_in_a_review_or_without_about(self):
        os.environ["BALOO_SESSION_REVIEW"] = "1"
        self.assertEqual(self.call("Read", "src/pay/charge.go"), "")
        del os.environ["BALOO_SESSION_REVIEW"]
        os.rename(os.path.join(self.dir, ".about"), os.path.join(self.dir, "about"))
        self.assertNamesNone("Read", "src/pay/charge.go")


class ThisRepo(unittest.TestCase):
    # A Guideline's file is in the folder ADR guidelines names.
    def test_names_the_guidelines_adr_at_a_guideline(self):
        in_repo(self)
        os.environ["CLAUDE_PROJECT_DIR"] = ROOT

        def call():
            stdin = json.dumps({
                "session_id": "s1", "tool_name": "Read",
                "tool_input": {"file_path": os.path.join(ROOT, "plugins/louie/guidelines/go.md")},
            })
            code, out, err = run("post-tool-use", stdin=stdin)
            self.assertEqual((code, err), (0, ""))
            return out

        self.assertIn(".about/adr/guidelines.md: ", call())
        self.assertNotIn(".about/adr/guidelines.md", call())


if __name__ == "__main__":
    unittest.main()
