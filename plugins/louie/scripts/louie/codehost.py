"""The tools of louie's MCP server `code-host`: what a stage of `implement` or `merge` asks the
Code host, on GitHub through `gh` and on Bitbucket Cloud through its API, with the rules a merge
rests on held here rather than in the implementer's text (PRD code-host, ADR code-host).

Each tool takes `dir`, a checkout or a worktree whose remote `origin` names the Code host, and
returns a dict: its answer, or `error` with a `message`. The token is never in what it returns."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

# args, cwd, stdin -> exit code, stdout, stderr
Run = Callable[[List[str], str, Optional[str]], Tuple[int, str, str]]
# method, url, headers, body -> status, headers, body
Http = Callable[[str, str, Dict[str, str], Optional[bytes]], Tuple[int, Dict[str, str], bytes]]

API = "https://api.bitbucket.org/2.0/repositories/"
TOKEN = "BITBUCKET_TOKEN"
EMAIL = "BITBUCKET_EMAIL"
GITHUB_METHODS = ("merge", "squash", "rebase")
BITBUCKET_METHODS = (
    "merge_commit", "squash", "fast_forward", "squash_fast_forward", "rebase_fast_forward",
    "rebase_merge",
)
# How long a Bitbucket merge the API queued is followed, polled every two seconds.
QUEUED_MERGE_SECONDS = 60
# pr_checks waits while a check runs, or while none shows, as one can show up minutes after a
# push, for the seconds its caller gives, up to five minutes a call,
# reading the checks again this often: a stage can't wait in one Bash call on a tool, and a tool
# call far longer than a Bash one risks the client's timeout.
CHECKS_POLL_SECONDS = 20
CHECKS_MAX_WAIT = 300

PASSED, FAILED, RUNNING, NONE = "passed", "failed", "running", "none"


class Failure(Exception):
    """A tool's call that can't go on: `code` names why, `message` says it for the agent."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def call(
    tool: str,
    params: Mapping[str, Any],
    env: Optional[Mapping[str, str]] = None,
    run: Optional[Run] = None,
    http: Optional[Http] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Runs the tool `tool` with `params` and returns its answer, the token masked in it."""
    env = os.environ if env is None else env
    # A value set in a settings file can end in a newline, which no header may hold.
    token = env.get(TOKEN, "").strip()
    email = env.get(EMAIL, "").strip()
    secrets = [token, _basic(email, token)] if token and email else [token]
    try:
        if tool not in TOOLS:
            raise Failure("bad-call", "no tool %r" % tool)
        if not isinstance(params, Mapping):
            raise Failure("bad-call", "the arguments must be an object")
        dir = _text(params, "dir")
        origin = _origin(run or _run, dir)
        bb = bitbucket_repo(origin)
        if bb:
            host = Bitbucket(bb, token, email, http or _http, sleep)  # type: Any
        else:
            host = GitHub(run or _run, dir)
        result = getattr(host, tool)(params)
        if tool == "pr_checks":
            wait = min(_seconds(params.get("wait")), CHECKS_MAX_WAIT)
            spent = 0
            while result["status"] in (RUNNING, NONE) and spent + CHECKS_POLL_SECONDS <= wait:
                sleep(CHECKS_POLL_SECONDS)
                spent += CHECKS_POLL_SECONDS
                result = host.pr_checks(params)
    except Failure as e:
        result = {"error": e.code, "message": e.message}
    # Anything else, a body of another shape or a header the client refuses, is an answer too: an
    # exception would end the server for the rest of the session, and its traceback on stderr
    # could hold the token unmasked.
    except Exception as e:  # noqa: BLE001
        result = {"error": "internal", "message": "%s: %s" % (type(e).__name__, e)}
    return _masked(result, secrets)


def bitbucket_repo(url: str) -> Optional[Tuple[str, str]]:
    """The workspace and the repo of a Bitbucket Cloud remote URL, on bitbucket.org or its SSH
    hosts ssh.bitbucket.org and altssh.bitbucket.org, lowercased as Bitbucket's slugs are; or None
    for any other host, which louie takes for GitHub's, as it did before Bitbucket Cloud (PRD
    code-host)."""
    m = re.match(
        r"^(?:[a-z][a-z0-9+.-]*://)?(?:[^@/]+@)?(?:(?:alt)?ssh\.)?bitbucket\.org(?::\d+)?[:/]([^/]+)/([^/]+?)(?:\.git)?/?$",
        url.strip(),
    )
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def _origin(run: Run, dir: str) -> str:
    code, out, err = run(["git", "remote", "get-url", "origin"], dir, None)
    if code != 0 or not out.strip():
        raise Failure("no-origin", "%s has no remote origin: %s" % (dir, err.strip()))
    return out.strip()


def _basic(email: str, token: str) -> str:
    return base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")


def same_commit(a: str, b: str) -> bool:
    """Whether two shas, full or short, name one commit."""
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def _worst(checks: List[Dict[str, str]], queued: bool) -> Dict[str, Any]:
    """The checks read as one: failed when one failed, else running while one runs or a run for
    the head is queued, else passed, else none (PRD code-host)."""
    for state in (FAILED, RUNNING):
        for c in checks:
            if c["state"] == state:
                return {"status": state, "check": c["name"], "link": c["link"], "checks": checks}
    if queued:
        return {"status": RUNNING, "check": "", "link": "", "checks": checks}
    return {"status": PASSED if checks else NONE, "check": "", "link": "", "checks": checks}


class GitHub:
    """GitHub through `gh`, signed in by the person: louie holds no GitHub token."""

    def __init__(self, run: Run, dir: str):
        self.run = run
        self.dir = dir

    def gh(self, args: List[str], stdin: Optional[str] = None) -> Tuple[int, str, str]:
        return self.run(["gh"] + args, self.dir, stdin)

    def json(self, args: List[str]) -> Any:
        code, out, err = self.gh(args)
        if code != 0:
            raise Failure("gh", "gh %s failed: %s" % (" ".join(args[:2]), (err or out).strip()))
        try:
            return json.loads(out)
        except ValueError:
            raise Failure("gh", "gh %s returned no JSON: %s" % (" ".join(args[:2]), out[:200])) from None

    def repo(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        r = self.json(["repo", "view", "--json",
                       "defaultBranchRef,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed"])
        branch = (r.get("defaultBranchRef") or {}).get("name", "")
        tip = self.json(["api", "repos/{owner}/{repo}/branches/" + branch])
        allowed = {"merge": "mergeCommitAllowed", "squash": "squashMergeAllowed",
                   "rebase": "rebaseMergeAllowed"}
        return {"host": "github", "default_branch": branch,
                "tip": (tip.get("commit") or {}).get("sha", ""),
                "methods": [m for m in GITHUB_METHODS if r.get(allowed[m])]}

    def pr_open(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        args = ["pr", "create", "--head", _text(params, "branch"), "--base", _text(params, "base"),
                "--title", _text(params, "title"), "--body-file", "-"]
        if params.get("draft"):
            args.append("--draft")
        code, out, err = self.gh(args, str(params.get("body", "")))
        url = out.strip().splitlines()[-1] if out.strip() else ""
        m = re.search(r"/pull/(\d+)$", url)
        if code != 0 or not m:
            raise Failure("gh", "gh pr create failed: %s" % (err or out).strip())
        return {"number": int(m.group(1)), "url": url}

    def pr_read(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        pr = self.json(["pr", "view", str(_number(params)), "--json",
                        "number,url,state,isDraft,headRefName,headRefOid,baseRefName,title,body"])
        return {"number": pr.get("number"), "url": pr.get("url", ""),
                "state": {"OPEN": "open", "MERGED": "merged"}.get(pr.get("state"), "closed"),
                "draft": bool(pr.get("isDraft")), "branch": pr.get("headRefName", ""),
                "head": pr.get("headRefOid", ""), "base_branch": pr.get("baseRefName", ""),
                "title": pr.get("title", ""), "body": pr.get("body", "")}

    def pr_checks(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        head = _text(params, "head")
        # With --json, gh gives the checks on stdout whatever its exit code; with none it says so on
        # stderr.
        code, out, err = self.gh(["pr", "checks", str(_number(params)), "--json", "name,bucket,link"])
        if out.strip():
            try:
                rows = json.loads(out)
            except ValueError:
                raise Failure("gh", "gh pr checks returned no JSON: %s" % out[:200]) from None
        elif "no checks reported" in err:
            rows = []
        else:
            raise Failure("gh", "gh pr checks failed: %s" % err.strip())
        bucket = {"pass": PASSED, "skipping": PASSED, "fail": FAILED, "cancel": FAILED,
                  "pending": RUNNING}
        checks = [{"name": r.get("name", ""), "state": bucket.get(r.get("bucket"), RUNNING),
                   "link": r.get("link", "")} for r in rows]
        runs = self.json(["run", "list", "--commit", head, "--json", "status,name,url"])
        return _worst(checks, any(r.get("status") != "completed" for r in runs))

    def pr_merge(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        method, head, base = _text(params, "method"), _sha(params, "head"), _sha(params, "base")
        if method not in GITHUB_METHODS:
            raise Failure("bad-call", "%r isn't a GitHub merge method: %s" % (method, ", ".join(GITHUB_METHODS)))
        stop = _before_merge(self.pr_read(params), self.repo(params), head, base)
        if stop:
            return stop
        code, out, err = self.gh(["pr", "merge", str(_number(params)), "--" + method,
                                  "--match-head-commit", head])
        if code == 0:
            return {"status": "merged", "reason": ""}
        said = (err or out).strip()
        if "Head branch was modified" in said or "head commit" in said.lower():
            return {"status": "head-moved", "reason": said}
        return {"status": "refused", "reason": said}


def _before_merge(pr: Dict[str, Any], repo: Dict[str, Any], head: str, base: str) -> Optional[Dict[str, Any]]:
    """Why a merge must not go on, read right before it on either host, or None: only an open pull
    request whose head is the commit given, onto a default branch whose tip is the base given."""
    if pr["state"] != "open":
        return {"status": "refused", "reason": "the pull request is %s" % pr["state"]}
    if pr["base_branch"] != repo["default_branch"]:
        return {"status": "refused", "reason": "the pull request targets %s, not the default branch %s"
                % (pr["base_branch"], repo["default_branch"])}
    if not same_commit(pr["head"], head):
        return {"status": "head-moved", "reason": "its head is %s, not %s" % (pr["head"], head)}
    if not same_commit(repo["tip"], base):
        return {"status": "base-moved",
                "reason": "%s is at %s, not %s" % (repo["default_branch"], repo["tip"], base)}
    return None


class Bitbucket:
    """Bitbucket Cloud through its API, with the token in BITBUCKET_TOKEN: with BITBUCKET_EMAIL
    set too, an API token and its account's email (Basic auth); without it, a repository or
    workspace access token (Bearer)."""

    def __init__(self, repo: Tuple[str, str], token: str, email: str, http: Http,
                 sleep: Callable[[float], None]):
        self.base = API + "/".join(urllib.parse.quote(p, safe="") for p in repo)
        self.token = token
        self.email = email
        self.http = http
        self.sleep = sleep

    def request(self, method: str, path: str, body: Any = None) -> Tuple[int, Dict[str, str], Any]:
        if not self.token:
            raise Failure("no-token", "%s isn't set: louie reaches Bitbucket Cloud with the token in it" % TOKEN)
        if self.email:
            auth = "Basic " + _basic(self.email, self.token)
        else:
            auth = "Bearer " + self.token
        headers = {"Authorization": auth, "Accept": "application/json"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        url = path if path.startswith("https://") else self.base + path
        status, got, raw = self.http(method, url, headers, data)
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            parsed = {"raw": raw[:300].decode("utf-8", "replace")}
        return status, got, parsed

    def get(self, path: str) -> Any:
        status, _, body = self.request("GET", path)
        if status != 200:
            raise Failure("api", "GET %s: %d %s" % (path or "/", status, _said(body)))
        return body

    def values(self, path: str) -> List[Any]:
        """Each value of a paged list, following `next` for up to ten pages."""
        out = []  # type: List[Any]
        for _ in range(10):
            page = self.get(path)
            out += page.get("values") or []
            path = page.get("next") or ""
            if not path:
                break
        return out

    def repo(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        branch = (self.get("").get("mainbranch") or {}).get("name", "")
        b = self.get("/refs/branches/" + urllib.parse.quote(branch, safe=""))
        return {"host": "bitbucket", "default_branch": branch,
                "tip": (b.get("target") or {}).get("hash", ""),
                "methods": list(b.get("merge_strategies") or [])}

    def pr_open(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        status, _, pr = self.request("POST", "/pullrequests", {
            "title": _text(params, "title"), "description": str(params.get("body", "")),
            "source": {"branch": {"name": _text(params, "branch")}},
            "destination": {"branch": {"name": _text(params, "base")}},
            "close_source_branch": False, "draft": bool(params.get("draft")),
        })
        if status not in (200, 201):
            raise Failure("api", "opening the pull request: %d %s" % (status, _said(pr)))
        return {"number": pr.get("id"), "url": ((pr.get("links") or {}).get("html") or {}).get("href", "")}

    def pr_read(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        pr = self.get("/pullrequests/%d" % _number(params))
        source = pr.get("source") or {}
        short = (source.get("commit") or {}).get("hash", "")
        # The API gives the head abbreviated; the stages record and compare full shas.
        head = self.get("/commit/" + short).get("hash", short) if short else ""
        return {"number": pr.get("id"),
                "url": ((pr.get("links") or {}).get("html") or {}).get("href", ""),
                "state": {"OPEN": "open", "MERGED": "merged"}.get(pr.get("state"), "closed"),
                "draft": bool(pr.get("draft")), "branch": (source.get("branch") or {}).get("name", ""),
                "head": head,
                "base_branch": (((pr.get("destination") or {}).get("branch")) or {}).get("name", ""),
                "title": pr.get("title", ""), "body": pr.get("description", "")}

    def pr_checks(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        head = _text(params, "head")
        state = {"SUCCESSFUL": PASSED, "FAILED": FAILED, "STOPPED": FAILED, "INPROGRESS": RUNNING}
        checks = [{"name": s.get("name") or s.get("key", ""), "state": state.get(s.get("state"), RUNNING),
                   "link": s.get("url", "")}
                  for s in self.values("/commit/%s/statuses?pagelen=100" % head)]
        # A pipeline shows no build until it starts, so a pending one counts as running. A repo
        # without Pipelines answers with an error, which means no pipeline.
        try:
            pipelines = self.values("/pipelines?target.commit.hash=%s&pagelen=50" % head)
        except Failure:
            pipelines = []
        queued = any((p.get("state") or {}).get("name") in ("PENDING", "IN_PROGRESS")
                     and same_commit(((p.get("target") or {}).get("commit") or {}).get("hash", ""), head)
                     for p in pipelines)
        return _worst(checks, queued)

    def pr_merge(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        method, head, base = _text(params, "method"), _sha(params, "head"), _sha(params, "base")
        if method not in BITBUCKET_METHODS:
            raise Failure("bad-call", "%r isn't a Bitbucket merge strategy: %s" % (method, ", ".join(BITBUCKET_METHODS)))
        # The API can't match the head as gh's --match-head-commit does: it is read again right
        # before the merge, and the seconds between are accepted as ADR merge accepts the base's.
        stop = _before_merge(self.pr_read(params), self.repo(params), head, base)
        if stop:
            return stop
        status, headers, body = self.request(
            "POST", "/pullrequests/%d/merge" % _number(params),
            {"merge_strategy": method, "close_source_branch": False})
        if status == 202:
            return self.queued(headers.get("Location") or headers.get("location") or "")
        if status == 200:
            return {"status": "merged", "reason": ""}
        return {"status": "refused", "reason": "%d %s" % (status, _said(body))}

    def queued(self, location: str) -> Dict[str, Any]:
        """Follows a merge the API queued to its end."""
        if not location:
            return {"status": "refused", "reason": "the merge was queued with no status to follow"}
        for _ in range(QUEUED_MERGE_SECONDS // 2):
            status, _, body = self.request("GET", location)
            if status != 200:
                return {"status": "refused", "reason": "%d %s" % (status, _said(body))}
            task = body.get("task_status")
            if task == "SUCCESS":
                return {"status": "merged", "reason": ""}
            if task != "PENDING":
                return {"status": "refused", "reason": "the queued merge ended %s" % task}
            self.sleep(2)
        return {"status": "refused", "reason": "the queued merge didn't end in %d seconds, and may still "
                "merge: read the pull request on the Code host" % QUEUED_MERGE_SECONDS}


def _said(body: Any) -> str:
    """What an API error body says, in a line."""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return str(err.get("message") or err.get("detail") or err)
        return str(body.get("raw") or body)[:300]
    return str(body)[:300]


def _text(params: Mapping[str, Any], key: str) -> str:
    v = params.get(key)
    if not isinstance(v, str) or not v:
        raise Failure("bad-call", "%s is required" % key)
    return v


def _sha(params: Mapping[str, Any], key: str) -> str:
    """A full sha: a short one could match another commit, and Bitbucket has no exact match."""
    v = _text(params, key)
    if not re.match(r"^[0-9a-f]{40}$", v):
        raise Failure("bad-call", "%s must be a full 40-character sha" % key)
    return v


def _seconds(v: Any) -> int:
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0


def _number(params: Mapping[str, Any]) -> int:
    v = params.get("number")
    if isinstance(v, str) and v.lstrip("#").isdigit():
        v = int(v.lstrip("#"))
    if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
        raise Failure("bad-call", "number is required: the pull request's number")
    return v


def _masked(value: Any, secrets: List[str]) -> Any:
    """`value` with each secret, the token and its Basic auth, replaced in every string, even where
    an API or an exception repeated it."""
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "***")
        return value
    if isinstance(value, dict):
        return {k: _masked(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_masked(v, secrets) for v in value]
    return value


def _run(args: List[str], cwd: str, stdin: Optional[str] = None) -> Tuple[int, str, str]:
    if not os.path.isdir(cwd):
        raise Failure("bad-call", "%s isn't a folder" % cwd)
    try:
        # Never the server's own stdin, which carries the protocol.
        done = subprocess.run(
            args, cwd=cwd, input=stdin if stdin is not None else "", capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
    except FileNotFoundError:
        raise Failure("no-client", "%s isn't installed" % args[0]) from None
    except PermissionError as e:
        raise Failure("bad-call", "%s: %s" % (" ".join(args[:3]), e)) from None
    except subprocess.TimeoutExpired:
        raise Failure("timeout", "%s took over two minutes" % " ".join(args[:3])) from None
    return done.returncode, done.stdout, done.stderr


def _http(method: str, url: str, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()) if e.headers else {}, e.read()
    except (urllib.error.URLError, OSError) as e:
        raise Failure("network", "%s %s: %s" % (method, url.split("?")[0], e)) from None


_DIR = {"type": "string", "description": "the absolute path of a checkout or worktree whose remote origin is the repo"}
_NUMBER = {"type": "integer", "description": "the pull request's number"}

# Each tool as the server lists it: its name, what it does and its parameters (PRD code-host).
TOOLS = {
    "repo": {
        "description": "Read the repo on its Code host (GitHub, or Bitbucket Cloud when origin is "
                       "bitbucket.org): its default branch, that branch's tip (full sha) and the merge "
                       "methods the host allows, in the host's own terms.",
        "properties": {"dir": _DIR},
        "required": ["dir"],
    },
    "pr_open": {
        "description": "Open a pull request from a pushed branch, a draft when asked. Never asks the "
                       "host to delete the branch. Returns its number and URL.",
        "properties": {
            "dir": _DIR,
            "branch": {"type": "string", "description": "the pushed branch"},
            "base": {"type": "string", "description": "the branch to merge into, the default one"},
            "title": {"type": "string"},
            "body": {"type": "string", "description": "the description, as it is"},
            "draft": {"type": "boolean"},
        },
        "required": ["dir", "branch", "base", "title", "body"],
    },
    "pr_read": {
        "description": "Read a pull request: its URL, state (open, merged or closed), draft, branch, "
                       "head (full sha), base branch, title and body.",
        "properties": {"dir": _DIR, "number": _NUMBER},
        "required": ["dir", "number"],
    },
    "pr_checks": {
        "description": "Read a pull request's checks on its head: status failed when one failed "
                       "(with its name and link), else running while one runs or a run for the head is "
                       "queued, else passed (each a success, skipped or neutral), else none. With wait, "
                       "reads them again while running or none, for up to that many seconds (at most "
                       "300), as a check can show up minutes after a push; call it again to wait longer.",
        "properties": {"dir": _DIR, "number": _NUMBER,
                       "head": {"type": "string", "description": "the full sha of the pull request's head"},
                       "wait": {"type": "integer", "description": "seconds to wait while a check runs or none shows, at most 300"}},
        "required": ["dir", "number", "head"],
    },
    "pr_merge": {
        "description": "Merge a pull request by a method, only when its head is the commit given and "
                       "the default branch's tip is the base given; deletes no branch. status merged, "
                       "head-moved or base-moved (nothing merged), or refused with the host's reason.",
        "properties": {
            "dir": _DIR, "number": _NUMBER,
            "method": {"type": "string", "description": "the merge method in the host's terms: "
                       "merge, squash or rebase on GitHub; merge_commit, squash, fast_forward, "
                       "squash_fast_forward, rebase_fast_forward or rebase_merge on Bitbucket Cloud"},
            "head": {"type": "string", "description": "the full sha the last Verification passed"},
            "base": {"type": "string", "description": "the full sha of the default branch the rebase used"},
        },
        "required": ["dir", "number", "method", "head", "base"],
    },
}
