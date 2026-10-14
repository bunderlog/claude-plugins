# cspell:ignore AKIA IOSFODNN
import json
import os
import re
import subprocess
import time
import unittest

from baloo import cli, names, review
from tests import commands, testkit
from tests.commands import PLUGIN, RUN, in_repo, read, run, start, write

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

    # The status-line command shows the bars the Config of the repo it is in sets, in their
    # order.
    def test_bars(self):
        commands.env(self)
        dir = testkit.tempdir(self)
        os.mkdir(os.path.join(dir, ".git"))
        write(os.path.join(dir, names.CONFIG), "status-line:\n  bars: [7d, context]\n")
        os.environ["COLUMNS"] = "80"
        stdin = json.dumps({
            "workspace": {"current_dir": dir}, "context_window": {"used_percentage": 12},
            "rate_limits": {"five_hour": {"used_percentage": 55},
                            "seven_day": {"used_percentage": 81}},
        })
        _, out, err = run("status-line", stdin=stdin)
        self.assertEqual(
            COLORS.sub("", out).strip(), "7d ████████░░ 81% Ctx █░░░░░░░░░ 12%", err
        )


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
                "baloo:no-git-hook-bypass: git commit --no-verify bypasses the Git hooks. If it's "
                "really needed, ask the user to run it themselves with `! <command>`."
            ))),
            (bash("git status; cat .env"),
             ("deny", "baloo:no-secrets-in-context: .env" + env_file)),
            ('{"tool_name": "Read", "tool_input": {"file_path": "' + dir + '/.env"}}',
             ("deny", "baloo:no-secrets-in-context: " + dir + "/.env" + env_file)),
            ('{"tool_name": "Edit", "tool_input": {"file_path": "' + dir + '/.claude/baloo.yml"}}',
             ("", "")),
            (bash("claude plugin disable baloo@bunderlog"), ("", "")),
            (bash("git push -f"), ("", "")),
            (bash("git status"), ("", "")),
            ("nope", ("", "")),
            ('{"tool_name": "Bash", "tool_input": {"command": 1}}', ("", "")),
        ]:
            with self.subTest(stdin=stdin):
                self.assertEqual(pre_tool_use(self, stdin), want)

    # A Check the Config turns off doesn't run.
    def test_checks_off(self):
        dir = in_repo(self)
        write(
            os.path.join(dir, names.CONFIG),
            "claude-hooks:\n  no-git-hook-bypass: false\n  no-secrets-in-context: false\n",
        )
        for command in ["git commit --no-verify", "git push -f", "cat .env"]:
            with self.subTest(command=command):
                self.assertEqual(pre_tool_use(self, bash(command)), ("", ""))


class Check(unittest.TestCase):
    # A Git hook's Check the Config turns off passes everything, and conventional-commits takes
    # its settings from the Config.
    def test_takes_the_config(self):
        commands.env(self)
        dir = testkit.repo(self)
        commands.chdir(self, dir)
        message = os.path.join(testkit.tempdir(self), "COMMIT_EDITMSG")
        write(message, "wip: x\n")
        for config, want in [
            ("", 0),  # off without its key
            ("git-hooks:\n  conventional-commits: true\n", 1),
            ("git-hooks:\n  conventional-commits:\n    types: [wip]\n", 0),
            ("git-hooks:\n  conventional-commits: false\n", 0),
        ]:
            with self.subTest(config=config):
                write(os.path.join(dir, names.CONFIG), config)
                code, _, err = run("check", "conventional-commits", message)
                self.assertEqual(code, want, err)


class AllowGuideline(unittest.TestCase):
    # The Read Hook allows a Guideline file, and says nothing of any other file or call.
    def test_allow_guideline(self):
        commands.env(self)
        os.environ["CLAUDE_PLUGIN_ROOT"] = PLUGIN
        outside = os.path.join(testkit.tempdir(self), "secret.md")
        write(outside, "x")
        link = os.path.join(testkit.tempdir(self), "guideline.md")
        os.symlink(os.path.join(PLUGIN, "guidelines", "go.md"), link)

        def read_(path):
            return '{"tool_name": "Read", "tool_input": {"file_path": ' + json.dumps(path) + "}}"

        allow = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow",'
            '"permissionDecisionReason":"baloo: one of the plugin\'s own guidelines"}}\n'
        )
        go = os.path.join(PLUGIN, "guidelines", "go.md")
        for name, stdin, want in [
            ("a Guideline", read_(go), allow),
            ("a link to a Guideline", read_(link), allow),
            ("a file outside", read_(outside), ""),
            ("a way out of guidelines/",
             read_(os.path.join(PLUGIN, "guidelines", "..", ".claude-plugin", "plugin.json")), ""),
            ("the folder itself", read_(os.path.join(PLUGIN, "guidelines")), ""),
            ("a relative path", read_("guidelines/go.md"), ""),
            ("a missing Guideline", read_(os.path.join(PLUGIN, "guidelines", "nope.md")), ""),
            ("another tool",
             '{"tool_name": "Write", "tool_input": {"file_path": ' + json.dumps(go) + "}}", ""),
            ("not JSON", "nope", ""),
        ]:
            with self.subTest(name):
                self.assertEqual(run("allow-guideline", stdin=stdin), (0, want, ""))
        os.environ["CLAUDE_PLUGIN_ROOT"] = ""
        self.assertEqual(run("allow-guideline", stdin=read_(go))[1], "")


class SubagentStart(unittest.TestCase):
    # The verifier's SubagentStart Hook tells it the Guidelines the Config turns on, and says
    # nothing to another agent or with none on.
    def test_subagent_start(self):
        dir = in_repo(self)
        verifier = '{"agent_type": "baloo:verifier"}'
        self.assertEqual(run("subagent-start", stdin=verifier)[:2], (0, ""))
        write(os.path.join(dir, names.CONFIG), "guidelines:\n  go: true\n")
        for name, stdin, want in [
            ("the verifier", verifier,
             "- Writing Go: " + os.path.join(PLUGIN, "guidelines", "go.md")),
            ("another agent", '{"agent_type": "Explore"}', ""),
            ("not JSON", "nope", ""),
        ]:
            with self.subTest(name):
                code, out, _ = run("subagent-start", stdin=stdin)
                self.assertEqual(code, 0)
                if not want:
                    self.assertEqual(out, "")
                    continue
                hook = json.loads(out)["hookSpecificOutput"]
                self.assertEqual(hook["hookEventName"], "SubagentStart")
                self.assertTrue(hook["additionalContext"].endswith(want))


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
        self.assertTrue(err.startswith("baloo condense: open "), err)

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
        self.assertTrue(err.startswith("baloo condense: no sessions of "), err)


class SessionEnd(unittest.TestCase):
    # A session that ends in a repo whose Config turns the Session review on starts one; a session
    # start while it runs says so, and the prompt after it ends shows its Proposals, once; the
    # user's decision is logged by review-decision. A headless session is shown none.
    def test_session_end(self):
        dir = in_repo(self)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        config = os.path.join(dir, names.CONFIG)
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

    # review-decision outside a repo, or of a Proposal there isn't, fails and says why.
    def test_review_decision_fails(self):
        dir = in_repo(self)
        code, _, err = run("review-decision", "T", "P1", "rejected")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("baloo review-decision: "), err)
        os.environ["CLAUDE_PROJECT_DIR"] = commands.outside_repo(self)
        code, _, err = run("review-decision", "T", "P1", "rejected")
        self.assertEqual((code, err), (
            1, "baloo review-decision: " + os.environ["CLAUDE_PROJECT_DIR"] + " is not in a repo\n"
        ))
        self.assertTrue(dir)


class PostToolUse(unittest.TestCase):
    # Format on edit runs the Config's command on a file Claude edited in the repo, with its path,
    # and says nothing of how it went; a file outside the repo, or a Session review's edit, runs
    # nothing.
    def test_format_on_edit(self):
        dir = in_repo(self)
        config = os.path.join(dir, names.CONFIG)
        write(config, "format-on-edit: printf formatted >\n")

        def edit(path):
            write(path, "edited")
            stdin = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": path}})
            self.assertEqual(run("post-tool-use", stdin=stdin), (0, "", ""))

        inside = os.path.join(dir, ".claude", "src", "a.vue")
        outside = os.path.join(testkit.tempdir(self), "b.vue")
        edit(inside)
        edit(outside)
        self.assertEqual((read(inside), read(outside)), ("formatted", "edited"))
        os.environ[review.ENV] = "1"
        edit(inside)
        self.assertEqual(read(inside), "edited")
        os.environ[review.ENV] = ""
        write(config, "format-on-edit: exit 3\n")
        edit(inside)  # a failing command is said nothing of, too

    # A Read or an edit of a file in the repo gives Claude the Guidelines whose subject it is, once
    # a session, where the Config turns them on.
    def test_gives_guidelines(self):
        dir = in_repo(self)
        write(
            os.path.join(dir, names.CONFIG), "guidelines:\n  typescript: true\n  testing: false\n"
        )

        def call(tool, file):
            stdin = json.dumps({
                "session_id": "s1", "tool_name": tool,
                "tool_input": {"file_path": os.path.join(dir, file)},
            })
            code, out, err = run("post-tool-use", stdin=stdin)
            self.assertEqual((code, err), (0, ""))
            return out

        got = call("Read", "src/a.test.ts")
        self.assertIn('"hookEventName":"PostToolUse"', got)
        self.assertIn("The typescript Guideline applies to src/a.test.ts", got)
        self.assertNotIn("testing Guideline", got)
        self.assertEqual(call("Edit", "src/b.ts"), "")

    # A Bash command that failed, which Claude Code hands to PostToolUseFailure, gives Claude the
    # Guideline of its task in that Hook's answer.
    def test_gives_guidelines_by_command(self):
        dir = in_repo(self)
        write(os.path.join(dir, names.CONFIG), "guidelines:\n  debugging: true\n")
        stdin = json.dumps({
            "session_id": "s1", "hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
            "tool_input": {"command": "go test ./..."}, "error": "Exit code 1\nFAIL x",
        })
        code, out, err = run("post-tool-use", stdin=stdin)
        self.assertEqual((code, err), (0, ""))
        self.assertIn('"hookEventName":"PostToolUseFailure"', out)
        self.assertIn("The debugging Guideline applies to", out)


if __name__ == "__main__":
    unittest.main()
