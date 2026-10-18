# cspell:ignore dont ndont AKIA IOSFODNN

import os
import time
import unittest
from unittest import mock

from baloo import names, review
from tests import testkit


def fake_claude(test, reply):
    """A `claude` that writes what it was run with into the folder `seen`: its arguments, one per
    line, its folder, the Session review's own environment variable and its stdin; then replies
    `reply`."""
    seen = testkit.tempdir(test)
    claude = os.path.join(testkit.tempdir(test), "claude")
    script = (
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > {seen}/args\n"
        f"pwd > {seen}/pwd\n"
        f'echo "${review.ENV}" > {seen}/env\n'
        f"cat > {seen}/stdin\n"
        f"printf '{reply}'\n"
    )
    with open(claude, "w") as f:
        f.write(script)
    os.chmod(claude, 0o755)
    return claude, seen


def conversation(chars):
    """A Transcript of a session `chars` characters long in all, with a Secret."""
    text = "AKIA" + "IOSFODNN7EXAMPLE " + "x" * chars  # cspell:disable-line
    return '{"type":"user","message":{"content":"' + text + '"}}\n'


def wait(test, root, data):
    """Waits until no Session review of the repo at `root` runs."""
    deadline = time.time() + 5
    while time.time() < deadline:
        if not review.running(root, data):
            return
        time.sleep(0.02)
    test.fail("the Session review still runs after 5s")


def read(folder, name):
    try:
        with open(os.path.join(folder, name)) as f:
            return f.read()
    except OSError:
        return ""


def entrypoint(test, value):
    """Sets CLAUDE_CODE_ENTRYPOINT to `value` until the test `test` ends."""
    patcher = mock.patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": value})
    patcher.start()
    test.addCleanup(patcher.stop)


class Start(unittest.TestCase):
    # A review runs headless at the repo's root, may write only its Proposals, and keeps its reply
    # in a file of its own id, which the next review leaves alone.
    def test_runs_a_headless_review_that_writes_only_proposals(self):
        claude, seen = fake_claude(self, "P1 adds Order to the glossary.\\n")
        root = os.path.realpath(testkit.repo(self))
        data = testkit.tempdir(self)
        for session in ["aaaaaaaa-1", "bbbbbbbb-2"]:
            started = review.start(
                claude, "/plugins/baloo", root, data, session, conversation(3000)
            )
            self.assertTrue(started)
            wait(self, root, data)
        folder = review._folder(root, data)
        replies = sorted(n for n in os.listdir(folder) if n.endswith(".txt"))
        self.assertEqual(len(replies), 2, "want one reply per review")
        for r in replies:
            self.assertEqual(read(folder, r), "P1 adds Order to the glossary.\n")
        self.assertEqual(read(seen, "pwd"), root + "\n")
        self.assertEqual(read(seen, "env"), "1\n", "so the review starts no review of its own")
        self.assertTrue(
            read(seen, "stdin").startswith("user: ***** xxx"), "want the conversation masked"
        )
        args = read(seen, "args")
        for want in [
            "-p",
            "--plugin-dir\n/plugins/baloo\n",
            "--tools\nRead,Glob,Grep,Edit,Write,Skill\n",
            "--permission-mode\ndontAsk\n",
            "--output-format\njson\n",
            "--max-budget-usd\n3\n",
            "Edit(./.about/proposals/**)\n",
            "./.about/proposals/" + replies[1][: -len(".txt")] + ".md",
        ]:
            self.assertIn(want, args)
        for not_ in ["Bash", "glossary.md)", "inbox.md)", "adr/**)"]:
            self.assertNotIn(not_, args, "it writes only its Proposals")
        exclude = read(os.path.join(root, ".git", "info"), "exclude")
        self.assertTrue(
            "\n/.about/proposals\n" in exclude or exclude.startswith("/.about/proposals\n"),
            f"info/exclude = {exclude!r}; want the Proposals left out of git",
        )

    # A session too short to have settled much gets no review, nor does a headless one of any
    # kind: `claude -p`'s, or the Agent SDK's in TypeScript or in Python.
    def test_skips_a_short_or_headless_session(self):
        for name, entry, chars, want in [
            ("short", "cli", 1000, False),
            ("sdk-cli", "sdk-cli", 3000, False),
            ("sdk-ts", "sdk-ts", 3000, False),
            ("sdk-py", "sdk-py", 3000, False),
            ("cli", "cli", 3000, True),
            ("empty", "", 3000, True),
        ]:
            with self.subTest(name):
                claude, seen = fake_claude(self, "")
                root, data = testkit.repo(self), testkit.tempdir(self)
                transcript = (
                    '{"type":"user","entrypoint":"' + entry + '","message":{"content":"'
                    + "x" * chars + '"}}\n'
                )
                started = review.start(claude, "/plugins/baloo", root, data, "s", transcript)
                self.assertEqual(started, want)
                wait(self, root, data)
                self.assertEqual(os.path.exists(os.path.join(seen, "args")), want)


def turn(text):
    """A line of a Transcript: the user's prompt `text`."""
    return '{"type":"user","message":{"content":"' + text + '"}}\n'


class Runs(unittest.TestCase):
    def setUp(self):
        entrypoint(self, "cli")
        self.root = os.path.realpath(repo_with(self))
        self.data = testkit.tempdir(self)

    def start(self, reply, transcript, session="s1"):
        """Starts the review of `transcript` with a `claude` that replies `reply`, and waits for
        its end; returns whether it started and the folder of what `claude` was run with."""
        claude, seen = fake_claude(self, reply)
        started = review.start(claude, "/plugins/baloo", self.root, self.data, session, transcript)
        wait(self, self.root, self.data)
        return started, seen

    # A resumed session's review reads only what the last one didn't, after what that one read
    # for context; with too little new, none starts.
    def test_a_resumed_session_is_reviewed_from_where_the_last_review_stopped(self):
        first = turn("a" * 3000)
        self.start("{}", first)
        started, seen = self.start("{}", first + turn("b" * 3000))
        self.assertTrue(started)
        before, seam, after = read(seen, "stdin").partition(review._SEAM)
        self.assertTrue(seam, "want the line between what was read and what wasn't")
        self.assertIn("aaa", before)
        self.assertNotIn("bbb", before)
        self.assertIn("bbb", after)
        self.assertNotIn("aaa", after)
        self.assertIn("propose only from what follows it", read(seen, "args"))
        started, _ = self.start("{}", first + turn("b" * 3000) + turn("c" * 10))
        self.assertFalse(started, "too little new to review")

    # A review that failed is told once, with why; the next review of its session reads again what
    # it didn't, and the week's failures and cost add up.
    def test_a_failed_review_is_told_once_and_read_again(self):
        first = turn("a" * 3000)
        self.start('{"is_error":true,"subtype":"error_max_budget_usd","total_cost_usd":3.1}', first)
        got = show(self.root, self.data, "s9")
        self.assertIn("failed, so nothing of its session is proposed: it reached its budget of $3", got)
        self.assertNotIn("failed", show(self.root, self.data, "s10"), "told once")
        started, seen = self.start("{}", first + turn("b" * 10))
        self.assertTrue(started)
        self.assertNotIn(review._SEAM, read(seen, "stdin"), "want the failed part read again")
        self.assertEqual(review.week(self.root, self.data), (1, 3.1))

    # Why a review failed comes from its reply, or, without one, its errors; an earlier Release's
    # reply, plain text, and one that succeeded tell nothing.
    def test_why_a_review_failed(self):
        for reply, want in [
            ('{"is_error":true,"result":"Not logged in"}', "proposed: Not logged in: tell"),
            ('{"is_error":true,"errors":["API Error: 529"]}', "proposed: API Error: 529: tell"),
            ("", "proposed: it ended with no reply: tell"),
            ("P1 adds Order.", ""),
            ('{"is_error":false,"result":"P1 adds Order."}', ""),
        ]:
            with self.subTest(reply):
                self.data = testkit.tempdir(self)
                self.start(reply, turn("a" * 3000))
                got = show(self.root, self.data, "s")
                if want:
                    self.assertIn(want, got)
                else:
                    self.assertNotIn("the Session review", got)

    # A conversation longer than a review reads is told, once it ended, with how much was read.
    def test_a_conversation_read_only_in_part_is_told(self):
        self.start("{}", turn("a" * 210_000))
        self.assertIn("read only the last 200000 of the 210006 characters", show(self.root, self.data, "s"))

    # The review is told what the user rejected before, so it proposes none of it again.
    def test_a_review_is_told_what_the_user_rejected(self):
        review.decide(self.root, self.data, "R1", "P1", review.REJECTED)
        _, seen = self.start("{}", turn("a" * 3000))
        self.assertIn("propose none of them again:\n- inbox: No evals\n", read(seen, "args"))


PROPOSALS = """# Session review R1

## P1 · inbox · add · .about/inbox.md · No evals

Why: found and not fixed.

After:
~~~markdown
## No evals

2026-10-07 · session review

Nothing measures the skills.
~~~

## P2 · glossary · edit · .about/glossary.md · Order

Why: agreed.

Before:
~~~markdown
**Order**:
A thing.
~~~

After:
~~~markdown
**Order**:
A request to buy.
~~~

## P3 · adr · delete · .about/adr/gone.md · Gone

Before:
~~~markdown
An old rule.
~~~

## P4 · notes · add · notes.md · Elsewhere

After:
~~~markdown
x
~~~
"""


class Parse(unittest.TestCase):
    def test_parse(self):
        got = review.parse("R1", PROPOSALS)
        self.assertEqual(len(got), 4)
        self.assertEqual(
            got[1],
            review.Proposal(
                review="R1",
                id="P2",
                target="glossary",
                kind="edit",
                path=".about/glossary.md",
                title="Order",
                before="**Order**:\nA thing.\n",
                after="**Order**:\nA request to buy.\n",
            ),
        )
        self.assertEqual([p.problem == "" for p in got], [True, True, True, False])
        for bad in [
            "## P1 inbox add\n",
            "## P1 · adr · add · .about/adr/../x.md · X\nAfter:\n~~~\nx\n~~~\n",
            "## P1 · inbox · edit · .about/inbox.md · X\nAfter:\n~~~\nx\n~~~\n",
        ]:
            with self.subTest(bad):
                p = review.parse("R", bad)
                self.assertEqual(len(p), 1)
                self.assertNotEqual(p[0].problem, "")

    # A Proposal fenced with backticks, as a reviewer may write it, reads as one fenced with
    # tildes: a heading inside its After is its text, not a Proposal of its own.
    def test_backtick_fence(self):
        text = (
            "# Session review R\n\n## P1 · inbox · add · .about/inbox.md · X\n\nAfter:\n\n"
            "```markdown\n## X\n\n~~~\nkept\n~~~\n```\n"
        )
        got = review.parse("R", text)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].problem, "")
        self.assertEqual(got[0].after, "## X\n\n~~~\nkept\n~~~\n")


def repo_with(test):
    """A repo with an origin carrying a token, the glossary and the ADR the Proposals change, and
    their file."""
    root = testkit.repo(test)
    origin = "https://user:token@github.com/o/r.git"  # baloo:allow-secret: a fake token to drop
    testkit.git(root, "remote", "add", "origin", origin)
    for path, text in {
        names.GLOSSARY: "# Glossary\n\n**Order**:\nA thing.\n",
        names.ADRS + "gone.md": "# Gone\n\nAn old\nrule.\n",
        names.INBOX: "",
        names.PROPOSALS + "R1.md": PROPOSALS,
        names.PROPOSALS + "R0.md": "# Session review R0\n",
        names.PROPOSALS + "keep.txt": "",
    }.items():
        write(os.path.join(root, path), text)
    return root


def write(file, text):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w") as f:
        f.write(text)


def show(root, data, session):
    """What show tells the session `session`, as one text."""
    return "\n".join(review.show(root, data, session, "decide"))


class Show(unittest.TestCase):
    def setUp(self):
        entrypoint(self, "cli")

    # A headless session of any kind is shown no Proposal: `claude -p`'s, or the Agent SDK's in
    # TypeScript or in Python.
    def test_shows_none_in_a_headless_session(self):
        for entry, want in [
            ("sdk-cli", False),
            ("sdk-ts", False),
            ("sdk-py", False),
            ("cli", True),
            ("", True),
        ]:
            with self.subTest(entry):
                entrypoint(self, entry)
                got = show(repo_with(self), testkit.tempdir(self), "s")
                self.assertEqual("R1 P1 inbox add" in got, want, got)

    # The Proposals are shown once a session, until each is decided; the log gets a line a
    # decision, with the repo's origin; the file goes once each is decided and applied.
    def test_show_and_decide(self):
        root, data = repo_with(self), testkit.tempdir(self)
        got = show(root, data, "s1")
        for want in [
            "`decide <review> <id> accepted|accepted-edited|rejected|deferred`",
            "  R1 P1 inbox add .about/inbox.md: No evals\n",
            "  R1 P2 glossary edit .about/glossary.md: Order\n",
            "  R1 P3 adr delete .about/adr/gone.md: Gone\n",
            "  R1 P4: can't be read, its target is",
        ]:
            self.assertIn(want, got + "\n")
        self.assertEqual(show(root, data, "s1"), "", "nothing new in the same session")
        self.assertEqual(show(root, data, "s2"), got, "the same list in another session")

        # P2 applied in other words, which its Applied records, P3 deferred twice, then neither
        # deferred again nor accepted unread.
        write(
            os.path.join(root, names.GLOSSARY),
            "# Glossary\n\n**Order**:\nA customer's\nrequest to buy.\n",
        )
        file = os.path.join(root, names.PROPOSALS, "R1.md")
        with_applied = PROPOSALS.replace(
            "## P3 ",
            "Applied:\n~~~markdown\n**Order**:\nA customer's request to buy.\n~~~\n\n## P3 ",
            1,
        )
        steps = [
            ("P2", review.ACCEPTED_EDITED, "has no Applied block"),
            ("P2", review.ACCEPTED_EDITED, ""),
            ("P3", review.DEFERRED, ""),
            ("P3", review.DEFERRED, ""),
            ("P3", review.DEFERRED, "deferred 2 times already"),
            ("P4", review.ACCEPTED, "can't be read"),
            ("P9", review.REJECTED, "no proposal P9"),
            ("P1", "maybe", "is not accepted, accepted-edited, rejected or deferred"),
        ]
        for i, (id, decision, err) in enumerate(steps):
            if i == 1:
                write(file, with_applied)
            with self.subTest(step=i, id=id, decision=decision):
                if err:
                    with self.assertRaises(review.Error) as caught:
                        review.decide(root, data, "R1", id, decision)
                    self.assertIn(err, str(caught.exception))
                else:
                    review.decide(root, data, "R1", id, decision)
        got = show(root, data, "s4")
        self.assertIn("R1 P3 adr delete .about/adr/gone.md: Gone (deferred 2×)", got)
        self.assertNotIn("R1 P2", got)
        lines = read(os.path.dirname(review._log_file(data)), "session-review.log").strip()
        lines = lines.split("\n")
        self.assertEqual(len(lines), 3, "a line per decision logged")
        f = lines[0].split("\t")
        self.assertEqual(len(f), 7)
        self.assertEqual(
            f[1:],
            ["https://github.com/o/r.git", "R1", "P2", "glossary", "edit", "accepted-edited"],
        )

        # Accepting an add the file doesn't hold yet is a mismatch until it is applied.
        todo = review.decide(root, data, "R1", "P1", review.ACCEPTED)
        self.assertIn("accepted, but its After is not in .about/inbox.md", todo)
        self.assertIn(
            "mismatch: R1 P1, accepted, but its After is not in", show(root, data, "s4")
        )
        write(
            os.path.join(root, names.INBOX),
            "## No evals\n\n2026-10-07 · session review\n\nNothing measures the skills.\n",
        )
        write(os.path.join(root, names.ADRS, "gone.md"), "# Gone\n")
        review.decide(root, data, "R1", "P3", review.ACCEPTED)
        review.decide(root, data, "R1", "P4", review.REJECTED)
        self.assertFalse(
            os.path.exists(file), "want R1.md gone once each Proposal is decided and applied"
        )
        decided = os.path.join(review._folder(root, data), "decided")
        self.assertEqual(read(decided, "R1.md"), with_applied, "the file kept as it was decided")
        self.assertTrue(
            os.path.exists(os.path.join(root, names.PROPOSALS, "keep.txt")),
            "the folder went with a file still in it",
        )

    # An edit whose Before is gone is stale and can't be accepted; one applied with no decision
    # logged is a mismatch.
    def test_stale_and_undecided_proposals(self):
        root, data = repo_with(self), testkit.tempdir(self)
        write(os.path.join(root, names.GLOSSARY), "# Glossary\n\n**Order**:\nSomething else.\n")
        self.assertIn(
            "R1 P2 glossary edit .about/glossary.md: Order (stale: ", show(root, data, "s1")
        )
        with self.assertRaises(review.Error) as caught:
            review.decide(root, data, "R1", "P2", review.ACCEPTED)
        self.assertIn("stale", str(caught.exception))
        review.decide(root, data, "R1", "P2", review.REJECTED)
        write(
            os.path.join(root, names.INBOX),
            "## No evals\n\n2026-10-07 · session review\n\nNothing measures the skills.\n",
        )
        self.assertIn(
            "mismatch: R1 P1, its After is in .about/inbox.md, but no decision is logged",
            show(root, data, "s2"),
        )


class Decide(unittest.TestCase):
    # A log written before it had fields is moved aside, so each line of the log parses.
    def test_moves_an_old_log_aside(self):
        root, data = repo_with(self), testkit.tempdir(self)
        write(review._log_file(data), "--- 2026-10-05T19:12:20Z /x\n")
        review.decide(root, data, "R1", "P2", review.REJECTED)
        folder = os.path.dirname(review._log_file(data))
        self.assertEqual(read(folder, "session-review.log.old"), "--- 2026-10-05T19:12:20Z /x\n")
        self.assertEqual(read(folder, "session-review.log").count("\t"), 6)


class Repo(unittest.TestCase):
    # Without an origin, the log names the repo by its root.
    def test_repo(self):
        root = testkit.repo(self)
        self.assertEqual(review.repo(root), root)
        testkit.git(root, "remote", "add", "origin", "git@github.com:o/r.git")
        self.assertEqual(review.repo(root), "git@github.com:o/r.git")


if __name__ == "__main__":
    unittest.main()
