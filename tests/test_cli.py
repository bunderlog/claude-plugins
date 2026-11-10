import json
import os
import re
import subprocess
import time
import unittest

from baloo import cli, names
from tests import commands, testkit
from tests.commands import PLUGIN, RUN, in_repo, read, run, write

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
    # The verifier's SubagentStart Hook tells it the Guidelines that fit the repo, and says
    # nothing to another agent.
    def test_subagent_start(self):
        dir = in_repo(self)
        verifier = '{"agent_type": "baloo:verifier"}'
        write(os.path.join(dir, "go.mod"), "module x\n")
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


class SessionEnd(unittest.TestCase):
    # A format-on-edit key in an old Config runs nothing (PRD no-config).
    def test_format_on_edit(self):
        dir = in_repo(self)
        write(os.path.join(dir, names.CONFIG), "format-on-edit: printf formatted >\n")
        path = os.path.join(dir, "src", "a.txt")
        write(path, "edited")
        stdin = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": path}})
        self.assertEqual(run("post-tool-use", stdin=stdin), (0, "", ""))
        self.assertEqual(read(path), "edited")

    # A Read or an edit of a file in the repo gives Claude the Guidelines whose subject it is, once
    # a session, whatever an old Config turns off (PRD no-config); a Read gives no testing.
    def test_gives_guidelines(self):
        dir = in_repo(self)
        write(os.path.join(dir, names.CONFIG), "guidelines:\n  typescript: false\n")

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
