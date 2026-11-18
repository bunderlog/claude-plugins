import io
import json
import os
import time
import unittest
from datetime import datetime, timezone

from bagheera import assess, cli, prices, review
from tests import testkit

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def line(kind, content, at="2026-11-10T09:00:00.000Z", **extra):
    """A Transcript's line of the type `kind`, with the message `content`, at `at`."""
    return json.dumps({"type": kind, "cwd": "/repo", "entrypoint": "cli", "timestamp": at,
                       "message": {"role": kind, "content": content}, **extra})


def call(id, name, input, at="2026-11-10T09:00:00.000Z"):
    return line("assistant", [{"type": "tool_use", "id": id, "name": name, "input": input}], at)


def result(id, text="ok", error=False, at="2026-11-10T09:00:00.000Z", **extra):
    block = {"type": "tool_result", "tool_use_id": id, "content": text}
    if error:
        block["is_error"] = True
    return line("user", [block], at, **extra)


def response(id, model, input, output, cache_written=0, cache_read=0):
    """An assistant's message `id` of the model `model` that used those tokens."""
    usage = {"input_tokens": input, "output_tokens": output,
             "cache_creation_input_tokens": cache_written, "cache_read_input_tokens": cache_read}
    return json.dumps({"type": "assistant", "timestamp": "2026-11-10T09:00:00.000Z",
                       "message": {"id": id, "model": model, "role": "assistant", "usage": usage,
                                   "content": [{"type": "text", "text": "thinking it over"}]}})


def denied(id, check, target, plugin="bagheera"):
    return result(id, f"PreToolUse:Bash hook error: {plugin}:{check}: {target} is an env file: no",
                  error=True)


def given(text, at="2026-11-10T09:00:00.000Z", event="PostToolUse"):
    """The attachment a Hook of the event `event` added the context `text` in, at `at`."""
    return json.dumps({"type": "attachment", "cwd": "/repo", "entrypoint": "cli", "timestamp": at,
                       "attachment": {"type": "hook_additional_context", "hookEvent": event,
                                      "content": [text]}})


def guideline(name, file):
    return (f"louie:\nThe {name} Guideline applies to {file}, which you just read or changed; "
            f"follow it for the rest of this session:\n\n# {name}\n")


def hathi(check):
    """What a Git hook running `hathi` prints for the Check `check` it failed."""
    return f"{check}: \"Add x\" is not `type(scope): description`; run: hathi explain {check}"


def notification(id, status):
    return line("user", f"<task-notification>\n<task-id>w1</task-id>\n<tool-use-id>{id}"
                        f"</tool-use-id>\n<status>{status}</status>\n<summary>done</summary>\n"
                        "</task-notification>")


# The report's groups: the plugins', then `hathi`'s Checks', which is no plugin.
SECTIONS = ("baloo", "louie", "bagheera", "hathi")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class Assess(unittest.TestCase):
    def setUp(self):
        self.root = testkit.repo(self)
        self.data = testkit.tempdir(self)
        self.dir = testkit.tempdir(self)

    def session(self, id, *lines):
        """Counts the session `id` of the lines `lines`; its record, or None."""
        path = os.path.join(self.dir, id + ".jsonl")
        write(path, "\n".join(lines) + "\n")
        return assess.record(self.data, id, path, self.root)

    def report(self, days=30, evals=""):
        return assess.report(self.data, days, "", NOW, evals)

    def test_a_record_holds_no_text_of_the_session(self):
        r = self.session(
            "s1",
            line("user", "deploy with AKIAIOSFODNN7EXAMPLE and zebra-umbrella"),
            call("t1", "Bash", {"command": "echo zebra-umbrella AKIAIOSFODNN7EXAMPLE"}),
            result("t1", "zebra-umbrella AKIAIOSFODNN7EXAMPLE"),
        )
        self.assertIsNotNone(r)
        with open(os.path.join(self.data, "assessment", "sessions.jsonl")) as f:
            text = f.read()
        self.assertEqual(text.count("\n"), 1)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", text)
        self.assertNotIn("zebra-umbrella", text)
        self.assertNotIn("deploy", text)

    def test_a_headless_session_adds_no_record(self):
        headless = json.dumps({"type": "user", "entrypoint": "sdk-cli", "message": {"content": "x"}})
        self.assertIsNone(self.session("s1", headless))
        self.assertEqual(assess.records(self.data), [])

    def test_index_counts_edits_after_a_read_of_the_adr_naming_them(self):
        write(os.path.join(self.root, ".about/adr/orders.md"),
              "# Orders\n\nOrders live in `src/orders/` and `src/orders/place.go`.\n")
        adr = os.path.join(self.root, ".about/adr/orders.md")
        self.session(
            "s1",
            call("e1", "Edit", {"file_path": os.path.join(self.root, "src/orders/place.go")},
                 "2026-11-10T09:00:00.000Z"),
            result("e1"),
            call("r1", "Read", {"file_path": adr}, "2026-11-10T09:01:00.000Z"),
            result("r1"),
            call("e2", "Edit", {"file_path": os.path.join(self.root, "src/orders/place.go")},
                 "2026-11-10T09:02:00.000Z"),
            result("e2"),
            call("e3", "Write", {"file_path": os.path.join(self.root, "src/orders/cancel.go")},
                 "2026-11-10T09:03:00.000Z"),
            result("e3"),
            call("e4", "Edit", {"file_path": os.path.join(self.root, "README.md")},
                 "2026-11-10T09:04:00.000Z"),
            result("e4"),
        )
        self.assertIn("after a read of it: 2 of 3", self.report())

    def test_index_leaves_out_edits_to_a_worktrees_about_folder(self):
        write(os.path.join(self.root, ".about/adr/docs.md"),
              "# Docs\n\nPRDs live in `.about/prd/`, the code in `src/orders/`.\n")
        worktree = os.path.join(self.root, ".claude/worktrees/pr-1")
        self.session(
            "s1",
            call("e1", "Edit", {"file_path": os.path.join(worktree, ".about/prd/export.md")}),
            result("e1"),
            call("e2", "Edit", {"file_path": os.path.join(worktree, "src/orders/place.go")}),
            result("e2"),
        )
        self.assertIn("after a read of it: 0 of 1", self.report())

    def test_what_followed_a_denial(self):
        self.session(
            "s1",
            line("user", "show the env"),
            call("d1", "Bash", {"command": "cat .env"}),
            denied("d1", "no-secrets-in-context", ".env"),
            call("t2", "Bash", {"command": "grep KEY .env"}),
            result("t2"),
            line("user", "and the other one"),
            call("d2", "Bash", {"command": "cat other.env"}),
            denied("d2", "no-secrets-in-context", "other.env", plugin="baloo"),
        )
        report = self.report()
        self.assertIn("no-secrets-in-context: 2 (0): another-way 1, went-on 0, nothing 1", report)

    def test_labels_count_and_a_deleted_transcript_stays_unlabeled(self):
        self.session("s1", call("d1", "Bash", {"command": "cat .env"}),
                     denied("d1", "no-secrets-in-context", ".env"))
        self.session("s2", call("d2", "Bash", {"command": "cat .env"}),
                     denied("d2", "no-secrets-in-context", ".env"))
        self.assertEqual(assess.label(self.data, "s1", "d1", "false"), "")
        self.assertIn("no denial", assess.label(self.data, "s1", "d9", "real"))
        self.assertIn("real or false", assess.label(self.data, "s1", "d1", "maybe"))
        os.remove(os.path.join(self.dir, "s2.jsonl"))
        report = self.report()
        self.assertIn("real 0, false 1, unlabeled 1", report)
        self.assertIn("Denials to label (ADR checks): none", report)

    def test_a_record_outlives_its_transcript(self):
        self.session("s1", line("user", "hi", at="2026-09-01T09:00:00.000Z"))
        os.remove(os.path.join(self.dir, "s1.jsonl"))
        self.assertIn("(PRD assessment): 0 (0)", self.report(30))
        self.assertIn("(PRD assessment): 1 (0)", self.report(90))

    def test_a_proposal_waiting_ten_days(self):
        write(os.path.join(self.root, ".about/proposals/20261102T120000Z-s1.md"),
              "# Session review 20261102T120000Z-s1\n\n## P1 · glossary · add · .about/glossary.md"
              " · Order\n\nAfter:\n~~~markdown\n**Order**:\nA request to buy.\n~~~\n")
        self.session("s1", line("user", "hi"))
        self.assertIn(
            f"Proposals waiting (PRD visibility): 1, the longest 10 days, in "
            f"{os.path.basename(self.root)}", self.report())

    def test_skills_session_start_and_a_subagents_reads(self):
        write(os.path.join(self.root, ".about/prd/export.md"), "# Export\n\nIn `src/export/`.\n")
        prd = os.path.join(self.root, ".about/prd/export.md")
        sub = os.path.join(self.dir, "s1", "subagents", "agent-a.jsonl")
        write(sub, call("r1", "Read", {"file_path": prd}, "2026-11-10T09:00:00.000Z") + "\n"
              + result("r1") + "\n")
        start = {"hookEvent": "SessionStart", "type": "hook_additional_context",
                 "content": ["Guidelines, the rules\nmore", "bagheera:\nx"]}
        self.session(
            "s1",
            json.dumps({"type": "attachment", "attachment": start}),
            json.dumps({"type": "attachment", "attachment": {
                "hookEvent": "SessionStart", "type": "hook_success", "content": "baloo:\nADRs"}}),
            call("k1", "Skill", {"skill": "baloo:prd"}),
            call("k2", "Skill", {"skill": "someone:else"}),
            # `ticket`'s name before 0.68.0.
            call("k3", "Skill", {"skill": "baloo:issue"}),
            line("user", "<command-name>/bagheera:assess</command-name>"),
            call("e1", "Edit", {"file_path": os.path.join(self.root, "src/export/csv.go")},
                 "2026-11-10T09:05:00.000Z"),
            result("e1", at="2026-11-10T09:05:00.000Z"),
        )
        report = self.report()
        self.assertIn("  baloo:prd: 1 (0)", report)
        self.assertIn("  bagheera:assess: 1 (0)", report)
        self.assertIn("  baloo:ticket: 1 (0)", report)
        self.assertNotIn("baloo:issue", report)
        self.assertNotIn("someone:else", report)
        self.assertIn("  louie: 26 (0)", report)
        self.assertIn("  bagheera: 11 (0)", report)
        self.assertIn("  baloo: 11 (0)", report)
        self.assertIn("after a read of it: 1 of 1", report)

    def test_session_review_decisions(self):
        self.session("s1", line("user", "hi"))
        repo = review.repo(self.root)
        lines = [
            ["2026-11-01T10:00:00Z", repo, "R", "P1", "inbox", "add", "accepted"],
            ["2026-11-01T10:00:00Z", repo, "R", "P2", "adr", "edit", "accepted-edited"],
            ["2026-11-01T10:00:00Z", repo, "R", "P3", "glossary", "add", "rejected"],
            ["2026-09-20T10:00:00Z", repo, "Q", "P1", "inbox", "add", "deferred"],
            ["2026-11-01T10:00:00Z", "other", "R", "P4", "inbox", "add", "accepted"],
        ]
        write(os.path.join(self.data, "session-review", "session-review.log"),
              "".join("\t".join(f) + "\n" for f in lines))
        report = self.report()
        self.assertIn("  accepted: 2 (0)", report)
        self.assertIn("  rejected: 1 (0)", report)
        self.assertIn("  deferred: 0 (1)", report)
        self.assertIn("  Inbox items added: 1 (0)", report)

    def test_the_command_counts_transcripts_on_disk_once_and_labels(self):
        config = testkit.tempdir(self)
        os.environ["CLAUDE_CONFIG_DIR"] = config
        os.environ["CLAUDE_PLUGIN_DATA"] = self.data
        os.environ["CLAUDE_PROJECT_DIR"] = self.root
        folder = os.path.join(config, "projects", "-repo")
        session = json.dumps({"type": "user", "cwd": self.root, "entrypoint": "cli",
                              "timestamp": "2026-11-10T09:00:00.000Z", "message": {"content": "hi"}})
        write(os.path.join(folder, "old.jsonl"), session + "\n" + call(
            "d1", "Bash", {"command": "cat .env"}) + "\n" + denied(
            "d1", "no-secrets-in-context", ".env") + "\n")
        home = json.dumps({"type": "user", "cwd": config, "message": {"content": "hi"}})
        write(os.path.join(folder, "own.jsonl"), home + "\n")

        def cmd(*args):
            out, err = io.StringIO(), io.StringIO()
            return cli.run(list(args), io.StringIO(), out, err), out.getvalue(), err.getvalue()

        code, out, _ = cmd("assess", "--days", "3650")
        self.assertEqual(code, 0)
        self.assertEqual([r["session"] for r in assess.records(self.data)], ["old"])
        self.assertIn("old d1 no-secrets-in-context: Bash(cat .env)", out)
        os.remove(os.path.join(self.data, "assessment", "sessions.jsonl"))
        cmd("assess")
        self.assertEqual(assess.records(self.data), [])
        self.assertEqual(cmd("assess", "label", "old", "d1", "real")[0], 1)
        self.assertEqual(cmd("assess", "--days", "0")[0], 2)

    def test_stale_eval_suites_only_where_the_repo_has_evals(self):
        write(os.path.join(self.root, "plugins/baloo/skills/adr/SKILL.md"), "v1\n")
        write(os.path.join(self.root, "evals/adr/case/case.yaml"), "name: case\n")
        write(os.path.join(self.root, "evals/results/r1/aggregate-result.json"), json.dumps({
            "startedAt": "2020-01-01T00:00:00.000Z",
            "cases": [{"dir": "evals/adr/case", "aggregates": {"score": 1, "delta": 0.5}}],
        }))
        testkit.git(self.root, "add", ".")
        testkit.git(self.root, "commit", "-qm", "adr")
        self.assertIn("adr: changed", self.report(evals=self.root))
        self.assertIn("score 1, delta 0.5", self.report(evals=self.root))
        self.assertNotIn("Eval suites", self.report(evals=self.dir))

    def test_each_figure_names_what_it_decides_for(self):
        self.session("s1", line("user", "hi"))
        blocks = [b for b in self.report().split("\n\n") if b not in SECTIONS]
        firsts = [blocks[0].split("\n")[1]] + [b.split("\n")[0] for b in blocks[1:]]
        for first in firsts:
            self.assertRegex(first, r"^(PRD|ADR) |\((PRD|ADR) ", first)

    def test_a_git_hooks_failure_fixed_nothing_and_hathi_check_by_hand(self):
        self.session(
            "s1",
            call("c1", "Bash", {"command": "git add x && git commit -m 'Add x'"}),
            result("c1", hathi("conventional-commits"), error=True),
            call("c2", "Bash", {"command": "git commit -m 'feat: add x'"}),
            result("c2", "[main 1a2b3c4] feat: add x"),
        )
        self.session(
            "s2",
            call("c1", "Bash", {"command": "git -C /repo commit -m 'Add y'"}),
            result("c1", hathi("conventional-commits"), error=True),
            call("p1", "Bash", {"command": "git push origin main"}),
            result("p1", "To origin\n   1a2b3c4..5d6e7f8  main -> main"),
            call("h1", "Bash", {"command": "hathi check commit-msg msg.txt"}),
            result("h1", hathi("no-ai-coauthor"), error=True),
        )
        report = self.report()
        self.assertIn("Git hooks' failures (ADR git-hooks, ADR measurement), over 2 sessions (0):",
                      report)
        self.assertIn("  conventional-commits: 2 (0): fixed 1, nothing 1", report)
        self.assertNotIn("no-ai-coauthor", report)

    def test_a_failed_push_is_fixed_by_a_later_push_only(self):
        self.session(
            "s1",
            call("p1", "Bash", {"command": "git push origin main"}),
            result("p1", hathi("no-secrets-in-commits"), error=True),
            call("c1", "Bash", {"command": "git commit -m 'fix: drop the key'"}),
            result("c1", "[main 1a2b3c4] fix: drop the key"),
        )
        self.session(
            "s2",
            call("p1", "Bash", {"command": "git push origin main"}),
            result("p1", hathi("no-secrets-in-commits"), error=True),
            call("p2", "Bash", {"command": "git push origin main"}),
            result("p2", "To origin\n   1a2b3c4..5d6e7f8  main -> main"),
        )
        self.assertIn("  no-secrets-in-commits: 2 (0): fixed 1, nothing 1", self.report())

    def test_a_workflow_agents_failures_count_in_its_own_order(self):
        agent = os.path.join(self.dir, "s1", "subagents", "workflows", "wf_1", "agent-a.jsonl")
        write(agent, "\n".join([
            call("c1", "Bash", {"command": "git commit -m 'Add x'"}),
            result("c1", hathi("no-ai-coauthor"), error=True),
        ]) + "\n")
        self.session(
            "s1",
            call("c1", "Bash", {"command": "git commit -m 'feat: add x'"}),
            result("c1", "[main 1a2b3c4] feat: add x"),
        )
        self.assertIn("  no-ai-coauthor: 1 (0): fixed 0, nothing 1", self.report())

    def test_guidelines_before_the_first_edit_and_the_index_alone(self):
        ts = os.path.join(self.root, "src/a.ts")
        self.session(
            "s1",
            call("r1", "Read", {"file_path": ts}, "2026-11-10T09:00:00.000Z"),
            result("r1", at="2026-11-10T09:00:00.000Z"),
            given(guideline("typescript", "src/a.ts"), "2026-11-10T09:00:01.000Z"),
            call("e1", "Edit", {"file_path": ts}, "2026-11-10T09:01:00.000Z"),
            result("e1", at="2026-11-10T09:01:00.000Z"),
        )
        self.session(
            "s2",
            call("e1", "Edit", {"file_path": ts}, "2026-11-10T09:00:00.000Z"),
            result("e1", at="2026-11-10T09:00:00.000Z"),
            given(guideline("typescript", "src/a.ts"), "2026-11-10T09:00:01.000Z"),
            call("b1", "Bash", {"command": "make test"}, "2026-11-10T09:02:00.000Z"),
            result("b1", "FAIL", error=True, at="2026-11-10T09:02:00.000Z"),
            given(guideline("debugging", "`make test`"), "2026-11-10T09:02:01.000Z",
                  "PostToolUseFailure"),
        )
        self.session(
            "s3",
            given("Guidelines, the rules for typescript and testing\n"
                  + guideline("testing", "a test"), event="SessionStart"),
            call("r1", "Read", {"file_path": "/plugins/louie/0.1.0/guidelines/go.md"}),
            result("r1"),
        )
        report = self.report()
        self.assertIn("Guidelines in the context, sessions (ADR guidelines), over 3 sessions (0):",
                      report)
        self.assertIn("  typescript: 2 (0), before the first edit of its files 1 of 2 (0 of 0)",
                      report)
        self.assertIn("  debugging: 1 (0)\n", report)
        self.assertIn("  go: 1 (0), before the first edit of its files 0 of 0 (0 of 0)", report)
        self.assertNotIn("  testing:", report)

    def test_workflows_run_and_how_they_ended(self):
        self.session(
            "s1",
            call("w1", "Workflow", {"name": "louie:verify", "args": "HEAD"}),
            result("w1", "Workflow launched in background. Task ID: w1"),
            notification("w1", "completed"),
            call("w2", "Workflow", {"name": "louie:plan"}),
            result("w2", "Workflow launched in background. Task ID: w2"),
            call("w3", "Workflow", {"name": "someone:else"}),
            result("w3", "Workflow launched in background. Task ID: w3"),
            # `implement`'s name before 0.68.0.
            call("w4", "Workflow", {"name": "louie:deliver"}),
            result("w4", "Workflow launched in background. Task ID: w4"),
            notification("w4", "completed"),
        )
        report = self.report()
        self.assertIn("Workflows run (PRD delivery, ADR verify), over 1 session (0):", report)
        self.assertIn("  verify: 1 (0): completed 1, failed 0, stopped 0, no end 0", report)
        self.assertIn("  plan: 1 (0): completed 0, failed 0, stopped 0, no end 1", report)
        self.assertIn("  implement: 1 (0): completed 1, failed 0, stopped 0, no end 0", report)
        self.assertNotIn("deliver", report.replace("PRD delivery", ""))
        self.assertNotIn("someone", report)

    def test_a_workflows_cost_at_its_models_prices(self):
        def agent(run, id, meta, *lines):
            folder = os.path.join(self.dir, "s1", "subagents", "workflows", run)
            write(os.path.join(folder, f"agent-{id}.jsonl"), "\n".join(lines) + "\n")
            write(os.path.join(folder, f"agent-{id}.meta.json"), json.dumps(meta))

        priced = "claude-opus-5-5"
        # Claude Code repeats a message's usage on each of its lines; it counts once.
        agent("wf_1", "a", {"agentType": "louie:planner", "workflowPhase": "Plan",
                            "description": "plan the zebra-umbrella"},
              response("m1", priced, 600_000, 60_000), response("m1", priced, 600_000, 60_000),
              response("m2", priced, 400_000, 40_000),
              response("m3", "<synthetic>", 0, 0))
        agent("wf_2", "b", {"agentType": "louie:verifier", "workflowPhase": "Verify",
                            "description": "verify the zebra-umbrella"},
              response("m1", "claude-unknown-9", 2_000, 300))
        self.session(
            "s1",
            call("w1", "Workflow", {"name": "louie:plan"}),
            result("w1", "Workflow launched in background.", toolUseResult={"runId": "wf_1"}),
            notification("w1", "completed"),
            call("w2", "Workflow", {"name": "louie:verify"}),
            result("w2", "Workflow launched in background.", toolUseResult={"runId": "wf_2"}),
            call("w3", "Workflow", {"name": "louie:implement"}),
            result("w3", "Workflow launched in background.", toolUseResult={"runId": "../wf_1"}),
        )
        # Claude Opus 5.5 at $4 input and $20 output a million tokens (prices.READ).
        dollars = "$6.00"
        self.assertEqual(f"${prices.cost(priced, (1_000_000, 100_000, 0, 0)):,.2f}", dollars)
        report = self.report()
        self.assertIn(f"Workflows' cost (PRD assessment, PRD delivery), at Anthropic's prices of "
                      f"{prices.READ}, over 2 runs (0):", report)
        self.assertIn(f"  plan: {dollars} a run, {dollars} ($0.00), 1,100,000 tokens, costliest "
                      f"phase Plan {dollars}, 1,100,000 tokens", report)
        self.assertIn("  verify: 2,300 tokens a run, 2,300 tokens (0), no price known, costliest "
                      "phase Verify 2,300 tokens", report)
        self.assertNotIn("  verify: $", report)
        self.assertIn("  claude-unknown-9: 2,300 tokens (0), no price known: counted in tokens, not "
                      "dollars", report)
        self.assertNotIn("  implement: $", report)
        self.assertNotIn("<synthetic>", report)
        lines = report.split("\n")
        cost = next(i for i, x in enumerate(lines) if x.startswith("Workflows' cost"))
        self.assertEqual([p for p in SECTIONS if lines.index(p) < cost][-1], "louie")
        with open(os.path.join(self.data, "assessment", "sessions.jsonl")) as f:
            text = f.read()
        self.assertNotIn("zebra-umbrella", text)
        self.assertNotIn("description", text)

    def test_the_figures_stand_under_each_plugin(self):
        self.session(
            "s1",
            call("k1", "Skill", {"skill": "baloo:prd"}),
            call("k2", "Skill", {"skill": "louie:plan"}),
            call("k3", "Skill", {"skill": "bagheera:assess"}),
            call("d1", "Bash", {"command": "cat .env"}),
            denied("d1", "no-secrets-in-context", ".env"),
        )
        lines = self.report().split("\n")
        self.assertTrue(lines[0].startswith("bunderlog assessment: "), lines[0])
        at = [lines.index(p) for p in SECTIONS]
        self.assertEqual(at, sorted(at))

        def under(text):
            i = next(i for i, x in enumerate(lines) if x.startswith(text))
            return [p for p in SECTIONS if lines.index(p) < i][-1]

        self.assertEqual(under("  baloo:prd: "), "baloo")
        self.assertEqual(under("PRD index: "), "baloo")
        self.assertEqual(under("  louie:plan: "), "louie")
        self.assertEqual(under("Guidelines in the context"), "louie")
        self.assertEqual(under("  bagheera:assess: "), "bagheera")
        self.assertEqual(under("  no-secrets-in-context: "), "bagheera")
        self.assertEqual(under("Denials to label"), "bagheera")
        self.assertEqual(under("Git hooks' failures"), "hathi")

    def test_a_record_of_the_release_before_is_recounted_once(self):
        os.environ["CLAUDE_CONFIG_DIR"] = testkit.tempdir(self)
        os.environ["CLAUDE_PLUGIN_DATA"] = self.data
        os.environ["CLAUDE_PROJECT_DIR"] = self.root
        kept = os.path.join(self.dir, "kept.jsonl")
        write(kept, "\n".join([
            call("c1", "Bash", {"command": "git commit -m 'Add x'"}),
            result("c1", hathi("conventional-commits"), error=True),
        ]) + "\n")
        sessions = os.path.join(self.data, "assessment", "sessions.jsonl")
        old = {"start": "2026-11-10 09:00", "repo": review.repo(self.root), "root": self.root,
               "version": "0.64.1", "denials": [], "skills": [], "index": {"edits": 0,
               "read_before": 0}, "session_start": {}}
        write(sessions, "".join(json.dumps(dict(old, session=id, transcript=t)) + "\n" for id, t in (
            ("kept", kept), ("gone", os.path.join(self.dir, "gone.jsonl")))))

        def report():
            out = io.StringIO()
            self.assertEqual(cli.run(["assess", "--days", "3650"], io.StringIO(), out,
                                     io.StringIO()), 0)
            return out.getvalue()

        out = report()
        self.assertIn("Sessions counted (PRD assessment): 2 (0)", out)
        self.assertIn("Git hooks' failures (ADR git-hooks, ADR measurement), over 1 session (0):",
                      out)
        self.assertIn("  conventional-commits: 1 (0): fixed 0, nothing 1", out)
        self.assertIn("Guidelines in the context, sessions (ADR guidelines), over 1 session (0):",
                      out)
        report()
        with open(sessions) as f:
            self.assertEqual(f.read().count("\n"), 3)


class SessionEnd(unittest.TestCase):
    def setUp(self):
        self.root = testkit.repo(self)
        self.data = testkit.tempdir(self)
        os.environ.update({"CLAUDE_PLUGIN_DATA": self.data, "CLAUDE_PLUGIN_ROOT": self.data,
                           "CLAUDE_PROJECT_DIR": self.root, "CLAUDE_CODE_ENTRYPOINT": "cli",
                           "PATH": "/usr/bin:/bin"})
        os.environ.pop(review.ENV, None)
        self.transcript = os.path.join(testkit.tempdir(self), "s1.jsonl")
        write(self.transcript, line("user", "hi") + "\n")

    def end(self):
        text = json.dumps({"session_id": "s1", "transcript_path": self.transcript})
        out = io.StringIO()
        self.assertEqual(cli.run(["session-end"], io.StringIO(text), out, io.StringIO()), 0)

    def wait(self):
        deadline = time.time() + 10
        while time.time() < deadline:
            if assess.records(self.data):
                return assess.records(self.data)
            time.sleep(0.05)
        return []

    def test_the_session_is_counted_once_it_ends(self):
        self.end()
        self.assertEqual([r["session"] for r in self.wait()], ["s1"])

    def test_no_count_in_a_headless_session_a_session_review_or_outside_a_repo(self):
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.end()
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        os.environ[review.ENV] = "1"
        self.end()
        del os.environ[review.ENV]
        os.environ["CLAUDE_PROJECT_DIR"] = testkit.tempdir(self)
        self.end()
        # A session counted after them is the only record, once its count is written.
        os.environ["CLAUDE_PROJECT_DIR"] = self.root
        text = json.dumps({"session_id": "s2", "transcript_path": self.transcript})
        cli.run(["session-end"], io.StringIO(text), io.StringIO(), io.StringIO())
        self.assertEqual([r["session"] for r in self.wait()], ["s2"])


if __name__ == "__main__":
    unittest.main()
