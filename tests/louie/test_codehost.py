"""louie's MCP server `code-host`: its tools on GitHub through `gh` and on Bitbucket Cloud through
its API, both stubbed, and the server spoken to over stdio (PRD code-host, ADR code-host)."""

import json
import os
import subprocess
import sys
import unittest

from louie import codehost
from tests import testkit
from tests.louie.commands import PLUGIN, RUN

HEAD = "a" * 40
BASE = "b" * 40
OTHER = "c" * 40
TOKEN = "ATATT3xSECRETVALUE0123456789"
GITHUB = "git@github.com:owner/repo.git"
BITBUCKET = "git@bitbucket.org:ws/repo.git"
API = "https://api.bitbucket.org/2.0/repositories/ws/repo"


class Stub:
    """`gh`, git and Bitbucket's API, answering from what a test sets and recording each call."""

    def __init__(self, origin=GITHUB):
        self.origin = origin
        self.commands = {}
        self.calls = []
        self.requests = []
        self.responses = {}

    def answer(self, prefix, code=0, out="", err=""):
        self.commands[tuple(prefix)] = (code, out if isinstance(out, str) else json.dumps(out), err)

    def run(self, args, cwd, stdin=None):
        self.calls.append((list(args), stdin))
        if args[:3] == ["git", "remote", "get-url"]:
            return (0, self.origin + "\n", "") if self.origin else (2, "", "error: No such remote")
        best = None
        for prefix in self.commands:
            if tuple(args[: len(prefix)]) == prefix and (best is None or len(prefix) > len(best)):
                best = prefix
        if best is None:
            return 127, "", "no stub for %s" % args
        return self.commands[best]

    def respond(self, method, path, status=200, body=None, headers=None):
        self.responses.setdefault((method, path), []).append(
            (status, headers or {}, json.dumps(body if body is not None else {}).encode())
        )

    def http(self, method, url, headers, body):
        self.requests.append((method, url, headers, json.loads(body) if body else None))
        path = url[len(API):] if url.startswith(API) else url
        queue = self.responses.get((method, path.split("?")[0]))
        if not queue:
            return 404, {}, b'{"error": {"message": "no stub"}}'
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def call(self, tool, env=None, **params):
        params.setdefault("dir", "/repo")
        return codehost.call(tool, params, env=env or {}, run=self.run, http=self.http,
                             sleep=lambda s: None)

    def ran(self, *prefix):
        return [a for a, _ in self.calls if tuple(a[: len(prefix)]) == prefix]


def github_pr(**over):
    pr = {"number": 7, "url": "https://github.com/owner/repo/pull/7", "state": "OPEN",
          "isDraft": False, "headRefName": "KAZ-1", "headRefOid": HEAD, "baseRefName": "main",
          "title": "T", "body": "Delivers KAZ-1."}
    pr.update(over)
    return pr


def github(pr=None, tip=BASE):
    s = Stub()
    s.answer(["gh", "repo", "view"], out={"defaultBranchRef": {"name": "main"},
                                          "mergeCommitAllowed": False, "rebaseMergeAllowed": True,
                                          "squashMergeAllowed": False})
    s.answer(["gh", "api", "repos/{owner}/{repo}/branches/main"], out={"commit": {"sha": tip}})
    s.answer(["gh", "pr", "view"], out=pr or github_pr())
    s.answer(["gh", "pr", "merge"], out="")
    return s


class Hosts(unittest.TestCase):
    # The Code host is told from origin's URL: bitbucket.org's is Bitbucket Cloud, any other GitHub.
    def test_bitbucket_cloud_from_its_urls(self):
        for url in (BITBUCKET, "https://bitbucket.org/ws/repo", "https://me@bitbucket.org/ws/repo.git",
                    "ssh://git@bitbucket.org/ws/repo.git", "git@ssh.bitbucket.org:ws/repo.git",
                    "ssh://git@altssh.bitbucket.org:443/ws/repo.git"):
            with self.subTest(url=url):
                self.assertEqual(codehost.bitbucket_repo(url), ("ws", "repo"))
        self.assertEqual(codehost.bitbucket_repo("git@ssh.bitbucket.org:CGS/WebUI.git"), ("cgs", "webui"))

    def test_github_from_any_other(self):
        for url in (GITHUB, "https://github.com/owner/repo", "git@github.example.com:o/r.git",
                    "gh-work:owner/repo.git", "https://notbitbucket.org/ws/repo"):
            with self.subTest(url=url):
                self.assertIsNone(codehost.bitbucket_repo(url))

    def test_a_folder_without_origin(self):
        s = Stub(origin="")
        self.assertEqual(s.call("repo")["error"], "no-origin")

    def test_an_unknown_tool(self):
        self.assertEqual(Stub().call("pr_close", number=1)["error"], "bad-call")


class GitHubRepo(unittest.TestCase):
    def test_repo_names_the_default_branch_its_tip_and_methods(self):
        self.assertEqual(github().call("repo"), {
            "host": "github", "default_branch": "main", "tip": BASE, "methods": ["rebase"]})


class GitHubOpen(unittest.TestCase):
    def test_opens_a_draft_with_the_body_on_stdin(self):
        s = github()
        s.answer(["gh", "pr", "create"], out="https://github.com/owner/repo/pull/9\n")
        got = s.call("pr_open", branch="KAZ-1", base="main", title="T", body="B", draft=True)
        self.assertEqual(got, {"number": 9, "url": "https://github.com/owner/repo/pull/9"})
        [(args, stdin)] = [c for c in s.calls if c[0][:3] == ["gh", "pr", "create"]]
        self.assertIn("--draft", args)
        self.assertEqual(stdin, "B")
        self.assertNotIn("--delete-branch", args)


class GitHubRead(unittest.TestCase):
    def test_reads_a_pull_request(self):
        got = github().call("pr_read", number=7)
        self.assertEqual(got, {"number": 7, "url": "https://github.com/owner/repo/pull/7",
                               "state": "open", "draft": False, "branch": "KAZ-1", "head": HEAD,
                               "base_branch": "main", "title": "T", "body": "Delivers KAZ-1."})

    def test_merged_and_closed(self):
        for state, want in (("MERGED", "merged"), ("CLOSED", "closed")):
            with self.subTest(state=state):
                self.assertEqual(github(github_pr(state=state)).call("pr_read", number=7)["state"], want)


class GitHubChecks(unittest.TestCase):
    def checks(self, rows, runs=(), code=0, err=""):
        s = github()
        s.answer(["gh", "pr", "checks"], code=code, out=list(rows) if rows is not None else "", err=err)
        s.answer(["gh", "run", "list"], out=[{"status": st, "name": "ci", "url": "u"} for st in runs])
        return s.call("pr_checks", number=7, head=HEAD)

    def test_passed_for_a_passed_and_a_skipped_check(self):
        got = self.checks([{"name": "test", "bucket": "pass", "link": "l1"},
                           {"name": "lint", "bucket": "skipping", "link": "l2"}], runs=["completed"])
        self.assertEqual(got["status"], "passed")

    def test_failed_names_the_check_and_its_link_also_while_another_runs(self):
        got = self.checks([{"name": "test", "bucket": "fail", "link": "l1"},
                           {"name": "lint", "bucket": "pending", "link": "l2"}], code=1)
        self.assertEqual((got["status"], got["check"], got["link"]), ("failed", "test", "l1"))

    def test_a_cancelled_check_failed(self):
        got = self.checks([{"name": "test", "bucket": "cancel", "link": "l1"}], code=1)
        self.assertEqual(got["status"], "failed")

    def test_running_while_one_runs(self):
        got = self.checks([{"name": "test", "bucket": "pending", "link": "l1"}], code=8)
        self.assertEqual(got["status"], "running")

    def test_running_while_a_run_for_the_head_is_queued_with_no_check_shown(self):
        got = self.checks(None, runs=["queued"], code=1, err="no checks reported on the 'KAZ-1' branch")
        self.assertEqual(got["status"], "running")

    def test_waits_while_running_up_to_the_seconds_given(self):
        s = github()
        s.commands[("gh", "pr", "checks")] = None  # answered by the queue below
        answers = [(8, json.dumps([{"name": "test", "bucket": "pending", "link": "l"}]), ""),
                   (0, json.dumps([{"name": "test", "bucket": "pass", "link": "l"}]), "")]
        run = s.run

        def queued(args, cwd, stdin=None):
            if args[:3] == ["gh", "pr", "checks"]:
                return answers.pop(0) if len(answers) > 1 else answers[0]
            return run(args, cwd, stdin)
        s.answer(["gh", "run", "list"], out=[])
        slept = []
        got = codehost.call("pr_checks", {"dir": "/repo", "number": 7, "head": HEAD, "wait": 60},
                            env={}, run=queued, http=s.http, sleep=slept.append)
        self.assertEqual(got["status"], "passed")
        self.assertEqual(sum(slept), codehost.CHECKS_POLL_SECONDS)

    def test_stops_waiting_once_the_seconds_are_spent(self):
        s = github()
        s.answer(["gh", "pr", "checks"], code=8, out=[{"name": "test", "bucket": "pending", "link": "l"}])
        s.answer(["gh", "run", "list"], out=[])
        slept = []
        got = codehost.call("pr_checks", {"dir": "/repo", "number": 7, "head": HEAD, "wait": 40},
                            env={}, run=s.run, http=s.http, sleep=slept.append)
        self.assertEqual(got["status"], "running")
        self.assertLessEqual(sum(slept), 40)

    def test_waits_while_none_shows_as_a_check_can_show_up_minutes_after_a_push(self):
        s = github()
        s.answer(["gh", "pr", "checks"], code=1, err="no checks reported on the 'KAZ-1' branch")
        s.answer(["gh", "run", "list"], out=[])
        slept = []
        got = codehost.call("pr_checks", {"dir": "/repo", "number": 7, "head": HEAD, "wait": 300},
                            env={}, run=s.run, http=s.http, sleep=slept.append)
        self.assertEqual((got["status"], sum(slept)), ("none", 300))

    def test_none_for_none(self):
        got = self.checks(None, code=1, err="no checks reported on the 'KAZ-1' branch")
        self.assertEqual(got["status"], "none")


class GitHubMerge(unittest.TestCase):
    def test_merges_matching_the_head_and_deletes_no_branch(self):
        s = github()
        got = s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "merged")
        [args] = s.ran("gh", "pr", "merge")
        self.assertEqual(args[3:], ["7", "--rebase", "--match-head-commit", HEAD])
        self.assertNotIn("--delete-branch", args)

    def test_base_moved_calls_no_merge(self):
        s = github(tip=OTHER)
        self.assertEqual(s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)["status"],
                         "base-moved")
        self.assertEqual(s.ran("gh", "pr", "merge"), [])

    def test_head_moved_before_the_merge_calls_no_merge(self):
        s = github(github_pr(headRefOid=OTHER))
        self.assertEqual(s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)["status"],
                         "head-moved")
        self.assertEqual(s.ran("gh", "pr", "merge"), [])

    def test_head_moved_when_gh_refuses_that_head(self):
        s = github()
        s.answer(["gh", "pr", "merge"], code=1,
                 err="GraphQL: Head branch was modified. Review and try the merge again. (mergePullRequest)")
        self.assertEqual(s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)["status"],
                         "head-moved")

    def test_refused_with_the_hosts_message(self):
        s = github()
        s.answer(["gh", "pr", "merge"], code=1, err="Pull request is not mergeable")
        got = s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "refused")
        self.assertIn("not mergeable", got["reason"])

    def test_a_method_the_host_doesnt_know(self):
        got = github().call("pr_merge", number=7, method="fast_forward", head=HEAD, base=BASE)
        self.assertEqual(got["error"], "bad-call")

    def test_a_pull_request_retargeted_to_another_branch_isnt_merged(self):
        s = github(github_pr(baseRefName="release"))
        got = s.call("pr_merge", number=7, method="rebase", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "refused")
        self.assertEqual(s.ran("gh", "pr", "merge"), [])

    def test_a_head_or_base_that_isnt_a_full_sha(self):
        for head, base in (("a", BASE), (HEAD, "b"), (HEAD[:12], BASE)):
            with self.subTest(head=head, base=base):
                got = github().call("pr_merge", number=7, method="rebase", head=head, base=base)
                self.assertEqual(got["error"], "bad-call")


def bitbucket(env=None):
    s = Stub(origin=BITBUCKET)
    s.env = {"BITBUCKET_TOKEN": TOKEN} if env is None else env
    s.respond("GET", "", body={"mainbranch": {"name": "main"}})
    s.respond("GET", "/refs/branches/main", body={
        "target": {"hash": BASE}, "merge_strategies": ["merge_commit", "squash"],
        "default_merge_strategy": "squash"})
    s.respond("GET", "/pullrequests/7", body=bitbucket_pr())
    s.respond("GET", "/commit/" + HEAD[:12], body={"hash": HEAD})
    return s


def bitbucket_pr(**over):
    pr = {"id": 7, "state": "OPEN", "draft": False, "title": "T", "description": "Delivers KAZ-1.",
          "source": {"branch": {"name": "KAZ-1"}, "commit": {"hash": HEAD[:12]}},
          "destination": {"branch": {"name": "main"}},
          "links": {"html": {"href": "https://bitbucket.org/ws/repo/pull-requests/7"}}}
    pr.update(over)
    return pr


def bb(s, tool, **params):
    return s.call(tool, env=s.env, **params)


class BitbucketAuth(unittest.TestCase):
    def test_bearer_without_an_email(self):
        s = bitbucket()
        bb(s, "repo")
        self.assertEqual(s.requests[0][2]["Authorization"], "Bearer " + TOKEN)

    def test_basic_with_an_email(self):
        s = bitbucket({"BITBUCKET_TOKEN": TOKEN, "BITBUCKET_EMAIL": "me@example.com"})
        bb(s, "repo")
        import base64
        want = "Basic " + base64.b64encode(("me@example.com:" + TOKEN).encode()).decode()
        self.assertEqual(s.requests[0][2]["Authorization"], want)

    def test_no_token_from_every_tool_and_no_api_called(self):
        s = bitbucket({})
        for tool, params in (("repo", {}), ("pr_read", {"number": 7}),
                             ("pr_open", {"branch": "b", "base": "main", "title": "t", "body": ""}),
                             ("pr_checks", {"number": 7, "head": HEAD}),
                             ("pr_merge", {"number": 7, "method": "squash", "head": HEAD, "base": BASE})):
            with self.subTest(tool=tool):
                self.assertEqual(bb(s, tool, **params)["error"], "no-token")
        self.assertEqual(s.requests, [])

    def test_the_token_is_in_no_answer_even_when_the_api_repeats_it(self):
        s = bitbucket()
        s.responses[("GET", "")] = [(401, {}, json.dumps(
            {"error": {"message": "bad token " + TOKEN}}).encode())]
        got = bb(s, "repo")
        self.assertEqual(got["error"], "api")
        self.assertNotIn(TOKEN, json.dumps(got))


class BitbucketTools(unittest.TestCase):
    def test_repo(self):
        self.assertEqual(bb(bitbucket(), "repo"), {
            "host": "bitbucket", "default_branch": "main", "tip": BASE,
            "methods": ["merge_commit", "squash"]})

    def test_opens_a_draft_never_closing_the_source_branch(self):
        s = bitbucket()
        s.respond("POST", "/pullrequests", status=201, body=bitbucket_pr(id=9, links={
            "html": {"href": "https://bitbucket.org/ws/repo/pull-requests/9"}}))
        got = bb(s, "pr_open", branch="KAZ-1", base="main", title="T", body="B", draft=True)
        self.assertEqual(got, {"number": 9, "url": "https://bitbucket.org/ws/repo/pull-requests/9"})
        sent = s.requests[-1][3]
        self.assertEqual((sent["draft"], sent["close_source_branch"]), (True, False))
        self.assertEqual(sent["source"]["branch"]["name"], "KAZ-1")
        self.assertEqual(sent["destination"]["branch"]["name"], "main")

    def test_reads_a_pull_request_with_its_full_head(self):
        got = bb(bitbucket(), "pr_read", number=7)
        self.assertEqual(got, {"number": 7, "url": "https://bitbucket.org/ws/repo/pull-requests/7",
                               "state": "open", "draft": False, "branch": "KAZ-1", "head": HEAD,
                               "base_branch": "main", "title": "T", "body": "Delivers KAZ-1."})

    def test_declined_is_closed(self):
        s = bitbucket()
        s.responses[("GET", "/pullrequests/7")] = [(200, {}, json.dumps(bitbucket_pr(state="DECLINED")).encode())]
        self.assertEqual(bb(s, "pr_read", number=7)["state"], "closed")

    def checks(self, statuses, pipelines=()):
        s = bitbucket()
        s.respond("GET", "/commit/%s/statuses" % HEAD, body={"values": statuses})
        s.respond("GET", "/pipelines", body={"values": [
            {"state": {"name": n}, "target": {"commit": {"hash": HEAD}}} for n in pipelines]})
        return bb(s, "pr_checks", number=7, head=HEAD)

    def test_a_stopped_or_failed_build_failed(self):
        for state in ("STOPPED", "FAILED"):
            with self.subTest(state=state):
                got = self.checks([{"name": "build", "state": state, "url": "u"},
                                   {"name": "lint", "state": "INPROGRESS", "url": "v"}])
                self.assertEqual((got["status"], got["check"], got["link"]), ("failed", "build", "u"))

    def test_a_pending_pipeline_with_no_build_shown_runs(self):
        self.assertEqual(self.checks([], pipelines=["PENDING"])["status"], "running")

    def test_passed_and_none(self):
        self.assertEqual(self.checks([{"name": "build", "state": "SUCCESSFUL", "url": "u"}],
                                     pipelines=["COMPLETED"])["status"], "passed")
        self.assertEqual(self.checks([])["status"], "none")

    def test_merges_by_the_method_never_closing_the_source_branch(self):
        s = bitbucket()
        s.respond("POST", "/pullrequests/7/merge", body=bitbucket_pr(state="MERGED"))
        got = bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "merged")
        sent = s.requests[-1][3]
        self.assertEqual((sent["merge_strategy"], sent["close_source_branch"]), ("squash", False))

    def test_head_moved_merges_nothing(self):
        s = bitbucket()
        s.responses[("GET", "/pullrequests/7")] = [(200, {}, json.dumps(bitbucket_pr(
            source={"branch": {"name": "KAZ-1"}, "commit": {"hash": OTHER[:12]}})).encode())]
        s.respond("GET", "/commit/" + OTHER[:12], body={"hash": OTHER})
        self.assertEqual(bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)["status"],
                         "head-moved")
        self.assertFalse([r for r in s.requests if r[0] == "POST"])

    def test_base_moved_merges_nothing(self):
        s = bitbucket()
        s.responses[("GET", "/refs/branches/main")] = [(200, {}, json.dumps({"target": {"hash": OTHER}}).encode())]
        self.assertEqual(bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)["status"],
                         "base-moved")
        self.assertFalse([r for r in s.requests if r[0] == "POST"])

    def test_a_queued_merge_is_followed_to_its_end(self):
        s = bitbucket()
        status = API + "/pullrequests/7/merge/task-status/t1"
        s.respond("POST", "/pullrequests/7/merge", status=202, headers={"Location": status})
        s.respond("GET", "/pullrequests/7/merge/task-status/t1", body={"task_status": "PENDING"})
        s.respond("GET", "/pullrequests/7/merge/task-status/t1", body={"task_status": "SUCCESS"})
        self.assertEqual(bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)["status"],
                         "merged")

    def test_a_queued_merge_that_fails_or_doesnt_end(self):
        s = bitbucket()
        status = API + "/pullrequests/7/merge/task-status/t1"
        s.respond("POST", "/pullrequests/7/merge", status=202, headers={"Location": status})
        s.respond("GET", "/pullrequests/7/merge/task-status/t1", body={"task_status": "FAILED"})
        self.assertEqual(bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)["status"], "refused")
        s = bitbucket()
        s.respond("POST", "/pullrequests/7/merge", status=202, headers={"Location": status})
        s.respond("GET", "/pullrequests/7/merge/task-status/t1", body={"task_status": "PENDING"})
        got = bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "refused")
        self.assertIn("may still merge", got["reason"])

    def test_refused(self):
        s = bitbucket()
        s.respond("POST", "/pullrequests/7/merge", status=400,
                  body={"error": {"message": "You can't merge until you have 1 approval"}})
        got = bb(s, "pr_merge", number=7, method="squash", head=HEAD, base=BASE)
        self.assertEqual(got["status"], "refused")
        self.assertIn("approval", got["reason"])

    def test_a_method_the_host_doesnt_know(self):
        got = bb(bitbucket(), "pr_merge", number=7, method="rebase", head=HEAD, base=BASE)
        self.assertEqual(got["error"], "bad-call")


class Robust(unittest.TestCase):
    def test_an_unexpected_failure_is_an_answer_with_the_token_masked(self):
        s = bitbucket()

        def broken(method, url, headers, body):
            raise ValueError("Invalid header value %r" % headers["Authorization"])
        got = codehost.call("repo", {"dir": "/repo"}, env={"BITBUCKET_TOKEN": TOKEN}, run=s.run, http=broken)
        self.assertEqual(got["error"], "internal")
        self.assertNotIn(TOKEN, json.dumps(got))

    def test_the_basic_header_is_masked_too(self):
        import base64
        s = bitbucket()
        env = {"BITBUCKET_TOKEN": TOKEN, "BITBUCKET_EMAIL": "me@example.com"}

        def broken(method, url, headers, body):
            raise ValueError("Invalid header value %r" % headers["Authorization"])
        got = codehost.call("repo", {"dir": "/repo"}, env=env, run=s.run, http=broken)
        basic = base64.b64encode(("me@example.com:" + TOKEN).encode()).decode()
        self.assertNotIn(basic, json.dumps(got))

    def test_a_token_with_a_newline_is_sent_without_it(self):
        s = bitbucket({"BITBUCKET_TOKEN": TOKEN + "\n"})
        bb(s, "repo")
        self.assertEqual(s.requests[0][2]["Authorization"], "Bearer " + TOKEN)

    def test_arguments_that_arent_an_object(self):
        self.assertEqual(codehost.call("repo", ["x"], env={}, run=Stub().run)["error"], "bad-call")

    def test_a_folder_that_isnt_there(self):
        got = codehost.call("repo", {"dir": "/no/such/folder"}, env={})
        self.assertEqual(got["error"], "bad-call")


class Server(unittest.TestCase):
    # Started as louie's manifest declares it, the server answers MCP over stdio.
    def test_speaks_mcp_over_stdio(self):
        with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            server = json.load(f)["mcpServers"]["code-host"]
        args = [a.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN) for a in server["args"]]
        self.assertEqual(server["command"], "python3")
        self.assertIn(RUN, args)
        repo = testkit.repo(self)
        testkit.git(repo, "remote", "add", "origin", GITHUB)
        bin_dir = testkit.tempdir(self)
        gh = os.path.join(bin_dir, "gh")
        with open(gh, "w") as f:
            f.write('#!/bin/sh\ncase "$2" in\n'
                    '  view) echo \'{"defaultBranchRef":{"name":"main"},"mergeCommitAllowed":true,'
                    '"rebaseMergeAllowed":false,"squashMergeAllowed":false}\' ;;\n'
                    '  *) echo \'{"commit":{"sha":"%s"}}\' ;;\nesac\n' % BASE)
        os.chmod(gh, 0o755)
        env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ.get("PATH", ""))
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "t", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "repo", "arguments": {"dir": repo}}},
            {"jsonrpc": "2.0", "id": 4, "method": "nope"},
        ]
        done = subprocess.run([sys.executable] + args, input="".join(json.dumps(m) + "\n" for m in messages),
                              capture_output=True, text=True, env=env, timeout=30)
        replies = {r["id"]: r for r in map(json.loads, done.stdout.splitlines())}
        self.assertEqual(sorted(replies), [1, 2, 3, 4], done.stderr)
        self.assertEqual(replies[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(replies[1]["result"]["serverInfo"]["name"], "code-host")
        tools = {t["name"]: t for t in replies[2]["result"]["tools"]}
        self.assertEqual(sorted(tools), ["pr_checks", "pr_merge", "pr_open", "pr_read", "repo"])
        for t in tools.values():
            self.assertIn("dir", t["inputSchema"]["required"])
        result = replies[3]["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"]), {
            "host": "github", "default_branch": "main", "tip": BASE, "methods": ["merge"]})
        self.assertEqual(replies[4]["error"]["code"], -32601)


class Stages(unittest.TestCase):
    # Every stage asks the Code host through the server: no stage names gh's own commands for it.
    def test_no_stage_names_the_hosts_client(self):
        for name in ("agents/implementer.md", "workflows/implement.js", "workflows/merge.js"):
            with self.subTest(file=name):
                with open(os.path.join(PLUGIN, name), encoding="utf-8") as f:
                    text = f.read()
                for banned in ("gh pr", "gh run", "gh repo"):
                    self.assertNotIn(banned, text)

    def test_the_implementer_may_call_the_servers_tools(self):
        with open(os.path.join(PLUGIN, "agents", "implementer.md"), encoding="utf-8") as f:
            tools = f.read().split("tools:", 1)[1].split("\n", 1)[0]
        self.assertIn("mcp__plugin_louie_code-host__*", tools)


if __name__ == "__main__":
    unittest.main()
