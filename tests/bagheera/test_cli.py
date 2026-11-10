import json
import os
import re
import subprocess
import time
import unittest

from bagheera import cli, names, review
from tests import testkit
from tests.bagheera import commands
from tests.bagheera.commands import PLUGIN, RUN, in_repo, run, start, write

COLORS = re.compile(r"\x1b\[[0-9;]*m")


def manifest_version():
    with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
        return json.load(f)["version"]


class Run(unittest.TestCase):
    def test_run(self):
        commands.env(self)
        for args, want in [
            (["version"], (0, manifest_version() + "\n", "")),
            ([], (2, "", cli.USAGE + "\n")),
            (["nope"], (2, "", cli.USAGE + "\n")),
            (["version", "extra"], (2, "", cli.USAGE + "\n")),
        ]:
            with self.subTest(args=args):
                self.assertEqual(run(*args), want)

    # The entry script runs the commands as the Hooks run it, with python3 -E -s.
    def test_entry_script(self):
        p = subprocess.run(
            ["python3", "-E", "-s", RUN, "version"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        self.assertEqual((p.returncode, p.stdout, p.stderr), (0, manifest_version() + "\n", ""))


class StatusLine(unittest.TestCase):
    # The status-line command prints the Status line for what Claude Code gives it, a field of
    # another type left out, and nothing for what isn't JSON.
    def test_status_line(self):
        commands.env(self)
        # 44 columns leave 40 for the line, which centers the 18 of the bar after 11 spaces.
        os.environ["COLUMNS"] = "44"
        for stdin, want in [
            ('{"context_window": {"used_percentage": 12}}', " " * 11 + "Ctx █░░░░░░░░░ 12%\n"),
            ('{"effort": "high", "context_window": {"used_percentage": 12}}',
             " " * 11 + "Ctx █░░░░░░░░░ 12%\n"),
            ("nope", ""),
        ]:
            with self.subTest(stdin=stdin):
                code, out, err = run("status-line", stdin=stdin)
                self.assertEqual((code, COLORS.sub("", out), err), (0, want, ""))

    # The status-line command shows its default bars, whatever an old Config of the repo it is in
    # sets (PRD no-config).
    def test_bars(self):
        commands.env(self)
        dir = testkit.tempdir(self)
        os.mkdir(os.path.join(dir, ".git"))
        os.environ["COLUMNS"] = "80"
        stdin = json.dumps({
            "workspace": {"current_dir": dir}, "context_window": {"used_percentage": 12},
            "rate_limits": {"five_hour": {"used_percentage": 55},
                            "seven_day": {"used_percentage": 81}},
        })
        _, plain, _ = run("status-line", stdin=stdin)
        write(os.path.join(dir, names.OLD_CONFIG), "status-line:\n  bars: [7d, context]\n")
        _, out, err = run("status-line", stdin=stdin)
        self.assertEqual((out, err), (plain, ""))
        self.assertIn("Ctx", COLORS.sub("", out))


def pre_tool_use(test, stdin):
    """The decision pre-tool-use prints for Claude Code on the tool call `stdin`, "" for none, with
    its reason."""
    code, out, err = run("pre-tool-use", stdin=stdin)
    test.assertEqual((code, err), (0, ""))
    if not out:
        return "", ""
    hook = json.loads(out)["hookSpecificOutput"]
    test.assertEqual(hook["hookEventName"], "PreToolUse")
    return hook["permissionDecision"], hook["permissionDecisionReason"]


def bash(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


class PreToolUse(unittest.TestCase):
    # pre-tool-use runs the Checks a Hook runs that the Config turns on, which are all of them
    # without a key, and only denies: it asks the user nothing (ADR measurement).
    def test_pre_tool_use(self):
        dir = in_repo(self)
        env_file = (
            " is an env file: showing it would put a secret into this session. If it's really "
            "needed, ask the user to look in their own terminal, not with `!`, whose output enters "
            "the session."
        )
        for stdin, want in [
            (bash("git commit --no-verify"), ("deny", (
                "bagheera:no-git-hook-bypass: git commit --no-verify bypasses the Git hooks. If it's "
                "really needed, ask the user to run it themselves with `! <command>`."
            ))),
            (bash("git status; cat .env"),
             ("deny", "bagheera:no-secrets-in-context: .env" + env_file)),
            ('{"tool_name": "Read", "tool_input": {"file_path": "' + dir + '/.env"}}',
             ("deny", "bagheera:no-secrets-in-context: " + dir + "/.env" + env_file)),
            ('{"tool_name": "Edit", "tool_input": {"file_path": "' + dir + '/.claude/baloo.yml"}}',
             ("", "")),
            (bash("claude plugin disable bagheera@bunderlog"), ("", "")),
            (bash("git push -f"), ("", "")),
            (bash("git status"), ("", "")),
            ("nope", ("", "")),
            ('{"tool_name": "Bash", "tool_input": {"command": 1}}', ("", "")),
        ]:
            with self.subTest(stdin=stdin):
                self.assertEqual(pre_tool_use(self, stdin), want)

    # A Check an old Config turns off still runs (PRD no-config).
    def test_checks_off(self):
        dir = in_repo(self)
        write(
            os.path.join(dir, names.OLD_CONFIG),
            "claude-hooks:\n  no-git-hook-bypass: false\n  no-secrets-in-context: false\n",
        )
        for command in ["git commit --no-verify", "cat .env"]:
            with self.subTest(command=command):
                self.assertEqual(pre_tool_use(self, bash(command))[0], "deny")


def condense_project(test):
    """A project folder, the folder commands run in until the test ends, whose Transcripts, in
    Claude Code's config folder, are the sessions "one" and "two", "two" the newer."""
    commands.env(test)
    config = testkit.tempdir(test)
    os.environ["CLAUDE_CONFIG_DIR"] = config
    project = testkit.tempdir(test)
    commands.chdir(test, project)
    transcripts = os.path.join(config, "projects", re.sub(r"[^A-Za-z0-9]", "-", project))
    for i, id in enumerate(["one", "two"]):
        path = os.path.join(transcripts, id + ".jsonl")
        write(path, '{"type":"user","message":{"content":"prompt of ' + id + " with AKIA"
              + 'IOSFODNN7EXAMPLE"}}\n')
        when = time.time() + (i - 2) * 3600
        os.utime(path, (when, when))
    return project, transcripts


class Condense(unittest.TestCase):
    # condense prints the latest session, the latest few with a summary, the sessions named, or
    # the lines around a moment of one, all masked.
    def test_condense(self):
        _, transcripts = condense_project(self)
        one = (
            "# Session one\n, 0 min, 0 tool calls, 0 failed\nTools: none\n\n"
            "[1] prompt: prompt of one with *****\n"
        )
        two = (
            "# Session two\n, 0 min, 0 tool calls, 0 failed\nTools: none\n\n"
            "[1] prompt: prompt of two with *****\n"
        )
        summary = "\n# Across 2 sessions\n"
        for args, want in [
            ([], two),
            (["--last", "5"], two + "\n" + one + summary),
            (["one"], one),
            ([os.path.join(transcripts, "one.jsonl"), "two"], one + "\n" + two + summary),
            (["two", "--around", "1"], "[1] user: prompt of two with *****\n"),
        ]:
            with self.subTest(args=args):
                self.assertEqual(run("condense", *args), (0, want, ""))
        code, _, err = run("condense", "nope")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("bagheera condense: open "), err)

    # Arguments condense can't read get the usage.
    def test_wrong_arguments(self):
        condense_project(self)
        for args in [["--last"], ["--last", "0"], ["two", "--around", "x"]]:
            with self.subTest(args=args):
                self.assertEqual(run("condense", *args)[0], 2)

    # Without the project's Transcripts, condense says where it looked.
    def test_without_transcripts(self):
        commands.env(self)
        os.environ["CLAUDE_CONFIG_DIR"] = testkit.tempdir(self)
        commands.chdir(self, testkit.tempdir(self))
        code, _, err = run("condense")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("bagheera condense: no sessions of "), err)


class SessionEnd(unittest.TestCase):
    # A session that ends in a repo whose Config turns the Session review on starts one; a session
    # start while it runs says so, and the prompt after it ends shows its Proposals, once; the
    # user's decision is logged by review-decision. A headless session is shown none.
    def test_session_end(self):
        dir = in_repo(self)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        config = os.path.join(dir, names.OLD_CONFIG)
        write(config, "session-review: true\n")
        bin = testkit.tempdir(self)
        proposal = (
            "# Session review T\n\n## P1 · glossary · add · .about/glossary.md · Order\n\n"
            "After:\n~~~markdown\n**Order**:\nA request to buy.\n~~~\n"
        )
        write(os.path.join(bin, "claude"), (
            "#!/bin/sh\ncat >/dev/null\nsleep 1\nmkdir -p .about/proposals\nprintf '%s' '"
            + proposal + "' > .about/proposals/T.md\necho 'P1 adds Order.'\n"
        ), 0o755)
        os.environ["PATH"] = bin + os.pathsep + os.environ["PATH"]
        transcript = os.path.join(testkit.tempdir(self), "s.jsonl")
        write(transcript, '{"type":"user","message":{"content":"' + "x" * 3000 + '"}}\n')
        end = json.dumps({"session_id": "s0", "transcript_path": transcript, "cwd": dir})
        self.assertEqual(run("session-end", stdin=end), (0, "", ""))
        code, out, _ = start(self)
        self.assertEqual(code, 0)
        self.assertIn("Session review of an earlier session is still running", out)

        def prompt():
            code, out, err = run("user-prompt-submit", stdin='{"session_id":"s1"}')
            self.assertEqual(code, 0, err)
            return out

        shown = ""
        deadline = time.time() + 5
        while not shown and time.time() < deadline:
            shown = prompt()
            time.sleep(0.05)
        self.assertIn('"hookEventName":"UserPromptSubmit"', shown)
        self.assertIn("T P1 glossary add .about/glossary.md: Order", shown)
        self.assertIn(
            "review-decision <review> <id> accepted|accepted-edited|rejected|deferred", shown
        )
        self.assertEqual(prompt(), "")

        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertNotIn("Session review", start(self)[1])
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        code, out, err = run("review-decision", "T", "P1", "rejected")
        self.assertEqual((code, out), (0, "logged T P1 rejected\n"), err)
        self.assertFalse(os.path.exists(os.path.join(dir, names.PROPOSALS, "T.md")))
        data = os.environ["CLAUDE_PLUGIN_DATA"]
        kept = [
            p for p in os.listdir(os.path.join(data, "session-review"))
            if os.path.exists(os.path.join(data, "session-review", p, "decided", "T.md"))
        ]
        self.assertEqual(len(kept), 1)

        # Its own end, and a Config that doesn't turn it on, start none.
        for value in ["1", ""]:
            with self.subTest(env=value):
                os.environ[review.ENV] = value
                if not value:
                    write(config, "session-review: false\n")
                run("session-end", stdin=end)
                self.assertNotIn("Session review", start(self)[1])

    # proposals lists the Proposals still waiting, a line each, for the inbox skill; outside a repo
    # it fails and says why.
    def test_proposals(self):
        dir = in_repo(self)
        write(os.path.join(dir, names.PROPOSALS, "T.md"), (
            "# Session review T\n\n## P1 · inbox · add · .about/inbox.md · Flaky suite\n\n"
            "After:\n~~~markdown\n## Flaky suite\n~~~\n"
        ))
        self.assertEqual(run("proposals"), (0, "T P1 inbox add .about/inbox.md: Flaky suite\n", ""))
        os.environ["CLAUDE_PROJECT_DIR"] = commands.outside_repo(self)
        self.assertEqual(run("proposals"), (
            1, "", "bagheera proposals: " + os.environ["CLAUDE_PROJECT_DIR"] + " is not in a repo\n"
        ))

    # review-decision outside a repo, or of a Proposal there isn't, fails and says why.
    def test_review_decision_fails(self):
        dir = in_repo(self)
        code, _, err = run("review-decision", "T", "P1", "rejected")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("bagheera review-decision: "), err)
        os.environ["CLAUDE_PROJECT_DIR"] = commands.outside_repo(self)
        code, _, err = run("review-decision", "T", "P1", "rejected")
        self.assertEqual((code, err), (
            1, "bagheera review-decision: " + os.environ["CLAUDE_PROJECT_DIR"] + " is not in a repo\n"
        ))
        self.assertTrue(dir)


    # A session running an older version than the one installed for the project is told, once,
    # to have the user restart, at its next prompt: no session start runs for it again.
    def test_prompt_names_a_newer_install(self):
        dir = in_repo(self)
        write(
            os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "plugins", "installed_plugins.json"),
            json.dumps({"plugins": {names.PLUGIN_ID: [
                {"scope": "local", "projectPath": dir, "version": "99.0.0"}
            ]}}),
        )

        def prompt():
            code, out, err = run("user-prompt-submit", stdin='{"session_id":"s1"}')
            self.assertEqual((code, err), (0, ""))
            return out

        out = prompt()
        self.assertIn('"hookEventName":"UserPromptSubmit"', out)
        self.assertIn("but 99.0.0 is installed for this project: tell the user to restart", out)
        self.assertNotIn("99.0.0", prompt())

if __name__ == "__main__":
    unittest.main()
