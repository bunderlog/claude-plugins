import json
import os
import time
import unittest
from unittest import mock

from bagheera import attention, names
from tests import testkit
from tests.bagheera import commands


def write(path, text, when=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if when is not None:
        os.utime(path, (when, when))


def entry(kind, stamp, cwd=""):
    e = {"type": kind, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(stamp))}
    if cwd:
        e["cwd"] = cwd
    return json.dumps(e) + "\n"


NOW = 1_800_000_000.0
DAY = 24 * 3600


class Projects(unittest.TestCase):
    # A repo a Transcript modified in the last 30 days was in is one of the machine's projects;
    # one only older Transcripts name, or a folder since removed, isn't; a subfolder and a linked
    # worktree count for the repo's main working tree.
    def test_projects(self):
        commands.env(self)
        config = testkit.tempdir(self)
        recent, old, sub = testkit.repo(self), testkit.repo(self), testkit.repo(self)
        os.makedirs(os.path.join(sub, "apps", "web"))
        testkit.git(recent, "commit", "-q", "--allow-empty", "-m", "x")
        tree = os.path.join(testkit.tempdir(self), "tree")
        testkit.git(recent, "worktree", "add", "-q", "-b", "work", tree)
        gone = os.path.join(testkit.tempdir(self), "gone")
        folder = os.path.join(config, "projects")
        write(os.path.join(folder, "a", "1.jsonl"), entry("user", NOW, recent), NOW - 29 * DAY)
        write(os.path.join(folder, "b", "2.jsonl"), entry("user", NOW, old), NOW - 31 * DAY)
        write(os.path.join(folder, "c", "3.jsonl"),
              '{"type": "queue-operation"}\n' + entry("user", NOW, os.path.join(sub, "apps", "web")),
              NOW)
        write(os.path.join(folder, "d", "4", "subagents", "5.jsonl"), entry("user", NOW, tree), NOW)
        write(os.path.join(folder, "e", "6.jsonl"), entry("user", NOW, gone), NOW)
        self.assertEqual(attention.projects(config, NOW), sorted([recent, sub]))

    def test_no_transcripts(self):
        self.assertEqual(attention.projects(testkit.tempdir(self), NOW), [])


class Needs(unittest.TestCase):
    def repo(self):
        dir = commands.in_repo(self)
        return dir, os.environ["CLAUDE_PLUGIN_DATA"]

    # A repo that isn't set up needs nothing for that; one set up but lacking attribution does,
    # with /bagheera:setup as the fix.
    def test_setup(self):
        dir, data = self.repo()
        self.assertEqual(attention.needs(dir, data), [])
        commands.set_up(dir)
        settings = os.path.join(dir, names.PROJECT_SETTINGS)
        with open(settings) as f:
            s = json.load(f)
        del s["attribution"]
        write(settings, json.dumps(s))
        got = attention.needs(dir, data)
        self.assertEqual([n.what for n in got], ["attribution off in .claude/settings.json is missing"])
        self.assertEqual(got[0].fix, names.SETUP_SKILL + " there")

    # A clone whose tracked Git hooks aren't turned on needs them on, until they are.
    def test_hooks_off(self):
        dir, data = self.repo()
        write(os.path.join(dir, ".githooks", "pre-commit"), "#!/bin/sh\n")
        testkit.git(dir, "add", ".githooks")
        self.assertEqual([n.fix for n in attention.needs(dir, data)],
                         ["git config core.hooksPath .githooks"])
        testkit.git(dir, "config", "core.hooksPath", ".githooks")
        self.assertEqual(attention.needs(dir, data), [])

    # An Inbox item not gone through needs attention; one kept after going through doesn't.
    def test_inbox(self):
        dir, data = self.repo()
        inbox = os.path.join(dir, names.INBOX)
        write(inbox, "## A\n\n2026-11-01 · user · kept 2026-11-09\n\nText.\n")
        self.assertEqual(attention.needs(dir, data), [])
        write(inbox, "## A\n\n2026-11-01 · user · kept 2026-11-09\n\n## B\n\n2026-11-10 · session\n")
        self.assertEqual([n.what for n in attention.needs(dir, data)],
                         ["1 Inbox item not gone through"])

    # A Proposal waiting needs attention.
    def test_proposals(self):
        dir, data = self.repo()
        write(os.path.join(dir, ".about", "glossary.md"), "# Glossary\n")
        write(os.path.join(dir, names.PROPOSALS, "20261110T000000Z-aaaaaaaa.md"),
              "# Session review 20261110T000000Z-aaaaaaaa\n\n"
              "## P1 · glossary · add · .about/glossary.md · Term\n\nWhy: x\n\n"
              "After:\n\n~~~markdown\n**Term**:\nA term.\n~~~\n")
        self.assertEqual([n.what for n in attention.needs(dir, data)], ["1 Proposal wait"])

    def test_inbox_left(self):
        for text, want in [
            ("", 0),
            ("## A\n", 1),
            ("## A\n## B\nx · kept 2026-01-01\n", 1),
            ("```\n## not\n```\n## A\n\nx · kept 2026-01-01\n", 0),
        ]:
            self.assertEqual(attention.inbox_left(text), want, text)


class Waits(unittest.TestCase):
    # A session marked waiting waits until its Transcript gets an entry of the person or of
    # Claude after the mark, its Claude Code exits, or the mark is cleared; Claude Code's own
    # entries after a turn's end don't count.
    def test_waits(self):
        data, folder = testkit.tempdir(self), testkit.tempdir(self)
        transcript = os.path.join(folder, "s.jsonl")
        write(transcript, entry("assistant", NOW - 5) + entry("system", NOW + 1))
        attention.mark(data, "s", folder, transcript, os.getpid(), NOW)
        self.assertEqual([w.session for w in attention.waits(data, NOW + 10)], ["s"])
        with open(transcript, "a") as f:
            f.write(entry("user", NOW + 20))
        self.assertEqual(attention.waits(data, NOW + 30), [])
        self.assertFalse(os.path.exists(os.path.join(data, attention.WAITING, "s")))

    def test_exited(self):
        data = testkit.tempdir(self)
        with mock.patch.object(attention, "_alive", lambda pid: pid != 4242):
            attention.mark(data, "gone", "", "", 4242, NOW)
            attention.mark(data, "here", "", "", 1, NOW)
            self.assertEqual([w.session for w in attention.waits(data, NOW)], ["here"])

    def test_clear(self):
        data = testkit.tempdir(self)
        attention.mark(data, "s", "", "", 0, NOW)
        attention.clear(data, "s")
        self.assertEqual(attention.waits(data, NOW), [])

    # The line counts every session waiting but its own.
    def test_found(self):
        found = attention.Found(NOW, [attention.Project("/a", True, [attention.Need("x", "y")]),
                                      attention.Project("/b", True)],
                                [attention.Wait("s1", "/a", NOW), attention.Wait("s2", "/b", NOW)])
        self.assertEqual(found.waiting("s1"), 1)
        self.assertEqual(found.waiting("other"), 2)
        self.assertEqual(found.attention(), 1)


class Check(unittest.TestCase):
    # What a check found is kept for the line, which reads it back; a second check isn't started
    # while the first is fresh.
    def test_check_and_read(self):
        commands.env(self)
        data, config = testkit.tempdir(self), testkit.tempdir(self)
        found = attention.check(data, config, NOW)
        self.assertEqual(attention.read(data), found)
        with mock.patch("subprocess.Popen") as popen:
            self.assertFalse(attention.start(data, "run.py", NOW + 1))
            self.assertTrue(attention.start(data, "run.py", NOW + attention.FRESH + 1))
            self.assertFalse(attention.start(data, "run.py", NOW + attention.FRESH + 2))
            self.assertEqual(popen.call_count, 1)

    # Neither the line nor doctor changes a project's files or git's config, or opens a socket:
    # a check writes only into the plugin's data folder.
    def test_reads_only(self):
        dir = commands.in_repo(self)
        commands.set_up(dir)
        write(os.path.join(dir, names.INBOX), "## A\n")
        write(os.path.join(dir, ".githooks", "pre-commit"), "#!/bin/sh\n")
        testkit.git(dir, "add", ".")
        config = os.environ["CLAUDE_CONFIG_DIR"]
        write(os.path.join(config, "projects", "p", "s.jsonl"), entry("user", NOW, dir), time.time())

        def state():
            files = {}
            for top, _, names_ in os.walk(dir):
                for n in names_:
                    path = os.path.join(top, n)
                    if "/.git/" in path and not path.endswith("/.git/config"):
                        continue
                    with open(path, "rb") as f:
                        files[path] = f.read()
            return files, testkit.git(dir, "config", "--list")

        before = state()
        with mock.patch("socket.socket", side_effect=AssertionError("a socket was opened")):
            found = attention.check(os.environ["CLAUDE_PLUGIN_DATA"], config, time.time())
            self.assertEqual(commands.run("doctor")[2], "")
        self.assertTrue(found.projects[0].needs)
        self.assertEqual(state(), before)

    def test_read_nothing(self):
        self.assertEqual(attention.read(testkit.tempdir(self)), attention.Found())


if __name__ == "__main__":
    unittest.main()
