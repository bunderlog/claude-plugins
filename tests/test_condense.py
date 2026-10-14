# cspell:ignore AKIA IOSFODNN MIIE

import json
import os
import tempfile
import time
import unittest

from baloo import condense


def transcript(*lines):
    """A Transcript of the lines `lines`, each a JSON object as Claude Code writes it."""
    return ("\n".join(lines) + "\n").encode()


START = '{"type":"user","cwd":"/repo","entrypoint":"cli","timestamp":"2026-10-01T09:00:00.000Z","message":{"role":"user","content":"add a retro skill to the plugin"}}'
TITLE = '{"type":"ai-title","aiTitle":"Port retro"}'
REPLY = '{"type":"assistant","timestamp":"2026-10-01T09:01:00.000Z","message":{"role":"assistant","content":[{"type":"text","text":"On it."},{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"go test ./..."}}]}}'
FAILED = '{"type":"user","timestamp":"2026-10-01T09:02:00.000Z","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t1","is_error":true,"content":"Exit code 1\\n--- FAIL: TestX\\nFAIL\\tpkg"}]}}'
PASSED = '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"t2","content":"ok"}]}}'
META = '{"type":"user","isMeta":true,"message":{"role":"user","content":"<local-command-caveat>Caveat</local-command-caveat>"}}'
SKILL = '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Base directory for this skill: /x\\n\\n# Retro"}]}}'
REMIND = '{"type":"user","message":{"role":"user","content":"<system-reminder>be brief</system-reminder>"}}'
STOP = '{"type":"user","timestamp":"2026-10-01T09:10:00.000Z","message":{"role":"user","content":[{"type":"text","text":"[Request interrupted by user]"}]}}'
CMD = '{"type":"user","message":{"role":"user","content":"<command-name>/baloo:interview</command-name>\\n<command-message>baloo:interview</command-message>\\n<command-args>port retro</command-args>"}}'


def failure(command, error):
    """A Transcript of one Bash call of `command` that failed with `error`."""
    use = {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": command}}
            ]
        },
    }
    result = {
        "type": "user",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": error}
            ]
        },
    }
    return transcript(json.dumps(use), json.dumps(result))


def usage(id, context):
    """The id and usage of a response `id` given a context of `context` tokens, which wrote
    100."""
    return (
        f'"id":"{id}","usage":{{"input_tokens":1,"cache_creation_input_tokens":{context - 1},'
        '"cache_read_input_tokens":0,"output_tokens":100}'
    )


def attachment(n):
    """A line of Claude Code's own whose attachment is `n` characters of text, or none."""
    if n == 0:
        return ""
    return (
        '{"type":"attachment","attachment":{"type":"total_tokens_reminder","text":"'
        + "a" * n
        + '"}}'
    )


def costly_with(grown, *after):
    """A Transcript where a Read of 30,000 characters and a Bash of 10,000, made in parallel, and
    the lines `after` grow the next response's context by `grown` tokens; the first response is
    written as two lines, as Claude Code does."""

    def result(id, chars):
        return f'{{"type":"tool_result","tool_use_id":"{id}","content":"{"x" * chars}"}}'

    lines = [
        '{"type":"assistant","cwd":"/repo","message":{'
        + usage("m1", 1000)
        + ',"content":[{"type":"text","text":"Reading."}]}}',
        '{"type":"assistant","cwd":"/repo","message":{'
        + usage("m1", 1000)
        + ',"content":[{"type":"tool_use","id":"r1","name":"Read","input":{"file_path":"/repo/big.go"}},'
        '{"type":"tool_use","id":"b1","name":"Bash","input":{"command":"ls"}}]}}',
        '{"type":"user","message":{"role":"user","content":['
        + result("r1", 30000)
        + ","
        + result("b1", 10000)
        + "]}}",
    ]
    lines += after
    lines.append(
        '{"type":"assistant","message":{'
        + usage("m2", 1000 + 100 + grown)
        + ',"content":[{"type":"text","text":"Done."}]}}'
    )
    return transcript(*lines)


def costly(grown, attached):
    """costly_with an attachment of `attached` characters."""
    return costly_with(grown, attachment(attached))


class Report(unittest.TestCase):
    def test_shows_the_sessions_prompts_commands_interrupts_and_failures(self):
        s = condense.condense(
            transcript(START, TITLE, REPLY, FAILED, PASSED, META, SKILL, REMIND, STOP, CMD), "abc"
        )
        self.assertEqual(
            s.report(),
            "# Session abc: Port retro\n"
            "2026-10-01 09:00, 10 min, 1 tool calls, 1 failed\n"
            "Tools: Bash 1\n"
            "\n"
            "[1] prompt: add a retro skill to the plugin\n"
            "[4] error exit Bash(go test ./...): Exit code 1: --- FAIL: TestX FAIL pkg\n"
            "[9] interrupt\n"
            "[10] command: /baloo:interview port retro",
        )

    def test_masks_secrets(self):
        prompt = (
            '{"type":"user","message":{"role":"user","content":"use sk-ant-'
            + "api03-" * 4
            + ' for it"}}'
        )
        self.assertIn(
            "[1] prompt: use ***** for it", condense.condense(transcript(prompt), "abc").report()
        )

    # A failed call's kind comes from its error, as Claude Code words it: a denial by one of the
    # plugin's Checks shows which one.
    def test_names_the_kind_of_each_failure(self):
        for error, want in [
            (
                "PreToolUse:Bash hook error: baloo:no-git-hook-bypass: git commit --no-verify "
                "bypasses the Git hooks.",
                "[2] error check Bash(x): PreToolUse:Bash hook error: baloo:no-git-hook-bypass: "
                "git commit --no-verify bypasses the Git hooks.",
            ),
            (
                "The user doesn't want to proceed with this tool use.",
                "[2] error rejected Bash(x): The user doesn't want to proceed with this tool use.",
            ),
            (
                "PreToolUse:Bash hook error: Blocked",
                "[2] error hook Bash(x): PreToolUse:Bash hook error: Blocked",
            ),
            (
                "Permission for this action was denied by the Claude Code auto mode classifier.",
                "[2] error classifier Bash(x): Permission for this action was denied by the "
                "Claude Code auto mode classifier.",
            ),
            (
                "This command requires approval",
                "[2] error permission Bash(x): This command requires approval",
            ),
            (
                "<tool_use_error>File has not been read yet.</tool_use_error>",
                "[2] error stale Bash(x): <tool_use_error>File has not been read yet."
                "</tool_use_error>",
            ),
            ("Exit code 2\n" + "x" * 250, "[2] error exit Bash(x): Exit code 2: …" + "x" * 200),
            ("MCP error -1: Failed", "[2] error other Bash(x): MCP error -1: Failed"),
        ]:
            with self.subTest(error=error[:40]):
                self.assertIn("\n" + want, condense.condense(failure("x", error), "abc").report())

    # A call made three times or more shows Claude hunting for the same thing.
    def test_shows_repeated_calls(self):
        lines = [
            '{"type":"assistant","cwd":"/repo","message":{"content":[{"type":"tool_use","id":"r%d",'
            '"name":"Read","input":{"file_path":"%s"}}]}}' % (i, path)
            for i, path in enumerate(["/repo/a.go", "/repo/a.go", "/repo/b.go", "/repo/a.go"])
        ]
        got = condense.condense(transcript(*lines), "abc").report()
        self.assertTrue(got.endswith("\n\nRepeated calls:\n3× Read(a.go)"), got)

    # A call's cost is what the next response's context grew by, beyond the last response's
    # output; calls made in parallel share it by the length of their results.
    def test_shows_expensive_calls(self):
        got = condense.condense(costly(20000, 0), "abc").report()
        want = (
            "\n\nExpensive calls, by the tokens they added to the context:\n"
            "[3] 15k Read(big.go)\n[3] 5k Bash(ls)"
        )
        self.assertTrue(got.endswith(want), got)


class Condense(unittest.TestCase):
    # A context that shrinks, after a compaction, charges nothing; a call under 5,000 tokens isn't
    # listed.
    def test_charges_no_shrink_and_lists_no_cheap_call(self):
        s = condense.condense(costly(-500, 0), "abc")
        self.assertEqual((s.costs, s.tokens), ([], {}))
        s = condense.condense(costly(4000, 0), "abc")
        self.assertEqual(s.costs, [])
        self.assertEqual(s.tokens["Read"], 3000)

    # What came with the results, Claude Code's attachments, takes its share by length.
    def test_charges_a_call_only_its_own_results_part(self):
        s = condense.condense(costly(20000, 40000), "abc")
        self.assertEqual(s.tokens, {"Read": 7500, "Bash": 2500})
        self.assertEqual(len(s.costs), 1)

    # What came with the results is measured by its text, as the results are, not by its JSON: an
    # attachment of 40,000 escaped quotes is 40,000 characters.
    def test_measures_an_attachment_by_its_text(self):
        quotes = (
            '{"type":"attachment","attachment":{"type":"hook_success","stdout":"'
            + '\\"' * 40000
            + '","exitCode":0}}'
        )
        s = condense.condense(costly_with(20000, quotes), "abc")
        self.assertEqual(s.tokens, {"Read": 7500, "Bash": 2500})

    # Claude Code's own messages, such as "No response requested.", carry no usage of their own:
    # the calls before one are charged by the next response.
    def test_skips_claude_codes_own_messages(self):
        own = (
            '{"type":"assistant","message":{"id":"s1","model":"<synthetic>","usage":'
            '{"input_tokens":0,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,'
            '"output_tokens":0},"content":[{"type":"text","text":"No response requested."}]}}'
        )
        s = condense.condense(costly_with(20000, own), "abc")
        self.assertEqual(s.tokens, {"Read": 15000, "Bash": 5000})

    # An image counts as about 1,500 tokens of text, however long its data: here as much as the
    # 6,000 characters of text beside it.
    def test_charges_an_image_by_an_estimate(self):
        image = (
            '{"type":"image","source":{"type":"base64","media_type":"image/png","data":"'
            + "A" * 190000
            + '"}}'
        )
        s = condense.condense(
            transcript(
                '{"type":"assistant","cwd":"/repo","message":{'
                + usage("m1", 1000)
                + ',"content":[{"type":"tool_use","id":"r1","name":"Read",'
                '"input":{"file_path":"/repo/shot.png"}}]}}',
                '{"type":"user","message":{"role":"user","content":[{"type":"tool_result",'
                '"tool_use_id":"r1","content":[' + image + "]}]}}",
                attachment(6000),
                '{"type":"assistant","message":{'
                + usage("m2", 1000 + 100 + 3000)
                + ',"content":[{"type":"text","text":"Done."}]}}',
            ),
            "abc",
        )
        self.assertEqual(s.tokens["Read"], 1500)


class Mask(unittest.TestCase):
    # Anything that may be a Secret is masked: a kind no-secrets-in-commits knows, however short, a
    # private key's whole block, and a long run of letters and digits mixed. Hex (a commit, a
    # session's id), words and file names stay.
    def test_masks_what_may_be_a_secret(self):
        for text, want in [
            ("key AKIA" + "IOSFODNN7EXAMPLE here", "key ***** here"),
            ("token ghp_" + "a1" * 18, "token *****"),
            (
                "-----BEGIN RSA "
                + "PRIVATE KEY-----\nMIIE\nabc\n-----END RSA PRIVATE KEY-----\nafter",
                "*****\nafter",
            ),
            ("x=" + "Xy1" * 11 + ";", "x=*****;"),
            ("commit " + "0123456789abcdef" * 3, "commit " + "0123456789abcdef" * 3),
            (
                "session 2551f813-9deb-4dea-8805-3a385154298a",
                "session 2551f813-9deb-4dea-8805-3a385154298a",
            ),
            (
                "TestLoader_without_shasum_or_sha_stops_before_downloading",
                "TestLoader_without_shasum_or_sha_stops_before_downloading",
            ),
            (
                "src/baloo/internal/condense/condense_test.go",
                "src/baloo/internal/condense/condense_test.go",
            ),
        ]:
            with self.subTest(text=text):
                self.assertEqual(condense.mask(text), want)

    # A private key's block with no end runs to the end of the text, its last newline too.
    def test_masks_a_private_key_without_its_end(self):
        self.assertEqual(
            condense.mask("before\n-----BEGIN " + "PRIVATE KEY-----\nMIIE\n"), "before\n*****"
        )


class Summary(unittest.TestCase):
    def test_shows_tokens_by_tool(self):
        got = condense.summary(
            [condense.condense(costly(20000, 0), "one"), condense.condense(costly(20000, 0), "two")]
        )
        want = (
            "\ntokens added to the context, by tool:\n"
            "  Read 30k in 2 session(s)\n"
            "  Bash 10k in 2 session(s)"
        )
        self.assertTrue(got.endswith(want), got)

    # Across sessions: failures by kind, the commonest kind first, each with its commonest
    # failures (a failed command by its tool, others by their error), then the prompts typed more
    # than once.
    def test_counts_failures_by_kind_and_repeated_prompts(self):
        def prompt(text):
            return '{"type":"user","message":{"role":"user","content":"' + text + '"}}'

        exit_ = failure("go test ./...", "Exit code 1\nFAIL")
        one = condense.condense(
            exit_ + transcript(prompt("run the checks and commit it"), prompt("yes")), "one"
        )
        two = condense.condense(
            exit_
            + failure("rm x", "This command requires approval")
            + transcript(prompt("Run the checks and commit it"), prompt("yes")),
            "two",
        )
        self.assertEqual(
            condense.summary([one, two]),
            "# Across 2 sessions\n"
            "exit: 2\n"
            "  2× in 2 session(s): Bash\n"
            "permission: 1\n"
            "  1× in 1 session(s): This command requires approval\n"
            "repeated prompts:\n"
            "  2× run the checks and commit it",
        )


class Around(unittest.TestCase):
    # Around shows a moment's lines in full, text, calls and results, each cut to 2000
    # characters, and masked: what a Retro reads instead of the raw Transcript.
    def test_shows_the_lines_around_a_moment_masked(self):
        long = '{"type":"assistant","message":{"content":[{"type":"text","text":"' + "y" * 2100 + '"}]}}'
        leak = (
            '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t9",'
            '"content":"AWS=AKIA' + 'IOSFODNN7EXAMPLE"}]}}'
        )
        tr = transcript(START, REPLY, FAILED, long, leak, STOP, CMD)
        self.assertEqual(
            condense.around(tr, 3, 2),
            "[1] user: add a retro skill to the plugin\n"
            "[2] assistant: On it.\n"
            "[2] assistant calls Bash(go test ./...)\n"
            "[3] user result (failed): Exit code 1\n--- FAIL: TestX\nFAIL\tpkg\n"
            "[4] assistant: " + "y" * 2000 + "\n"
            "[5] user result: AWS=*****",
        )


class Conversation(unittest.TestCase):
    # A Session review reads only what the user and Claude wrote, masked: no tool call or result,
    # and nothing Claude Code wrote in the user's turn but a command.
    def test_is_what_the_user_and_claude_wrote_masked(self):
        leak = (
            '{"type":"assistant","message":{"content":[{"type":"text","text":"Use AKIA'
            + 'IOSFODNN7EXAMPLE."}]}}'
        )
        got = condense.conversation(
            transcript(START, TITLE, REPLY, FAILED, PASSED, META, SKILL, REMIND, STOP, CMD, leak),
            1000,
        )
        self.assertEqual(
            got,
            "user: add a retro skill to the plugin\n\n"
            "assistant: On it.\n\n"
            "user: /baloo:interview port retro\n\n"
            "assistant: Use *****.",
        )
        self.assertEqual(condense.conversation(transcript(START, REPLY), 10), "nt: On it.")


class Transcripts(unittest.TestCase):
    def tempdir(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    # Claude Code keeps a project's Transcripts in projects/ under its config folder, in a folder
    # named after the project's path with each character but a letter or digit as `-`.
    def test_finds_the_projects_transcripts_from_it_or_a_folder_in_it(self):
        config = self.tempdir()
        want = os.path.join(config, "projects", "-home-me-my-repo-v2")
        os.makedirs(want)
        for cwd in ["/home/me/my_repo.v2", "/home/me/my_repo.v2/src/x"]:
            with self.subTest(cwd=cwd):
                self.assertEqual(condense.transcripts_folder(config, cwd), want)
        self.assertEqual(condense.transcripts_folder(config, "/home/me/other"), "")

    def test_latest_takes_the_newest_sessions_worth_a_retro(self):
        folder = self.tempdir()
        headless = '{"type":"user","entrypoint":"sdk-cli","message":{"content":"review the session"}}'
        clear = '{"type":"user","message":{"content":"<command-name>/clear</command-name>\\n<command-args></command-args>"}}'

        def write(id, text, ago):
            path = os.path.join(folder, id + ".jsonl")
            with open(path, "wb") as f:
                f.write(text)
            when = time.time() - ago
            os.utime(path, (when, when))

        write("old", transcript(START), 3 * 3600)
        write("older", transcript(START), 4 * 3600)
        write("new", transcript(START), 3600)
        write("headless", transcript(headless), 0)
        write("cleared", transcript(clear), 0)
        os.mkdir(os.path.join(folder, "new"))  # a session's subagents
        self.assertEqual([s.id for s in condense.latest(folder, 2)], ["new", "old"])


if __name__ == "__main__":
    unittest.main()
