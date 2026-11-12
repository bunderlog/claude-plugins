"""Counts each session at its end into bagheera's data folder, and reports from those counts how
useful each part of bunderlog is and how well it works (PRD assessment)."""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from bagheera import condense, names, repo, review, version

# The folder in the plugin's data folder that holds the records and the labels.
FOLDER = "assessment"
SESSIONS = "sessions.jsonl"
LABELS = "labels.jsonl"
# Marks that the sessions whose Transcripts were on disk before the first record are counted.
BACKFILLED = "backfilled"

REAL, FALSE = "real", "false"
# bunderlog's plugins, whose skills a record counts.
_PLUGINS = (names.PLUGIN, names.KNOWLEDGE, names.BUILD)
DAYS = 30

# The folders of a repo's ADRs and PRDs, whose files name the code they rest on (PRD index).
_KNOWLEDGE = (names.ADRS, names.PRDS)
# A path of two or more segments in an ADR's or a PRD's text.
_PATH = re.compile(r"[\w.@-]+(?:/[\w.@-]+)+")


def _folder(data: str) -> str:
    return os.path.join(data, FOLDER)


def start(data: str, script: str, session: str, transcript: str, root: str) -> None:
    """Starts counting the session `session`, whose Transcript is the file `transcript`, in the
    repo at `root`, in a process of its own that outlives Claude Code's exit; returns at once."""
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=data)
    subprocess.Popen(
        [sys.executable, "-E", "-s", script, "assess-count", session, transcript, root],
        env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )


def record(data: str, session: str, transcript: str, root: str) -> Optional[Dict[str, Any]]:
    """Counts the session `session` from its Transcript `transcript`, in the repo at `root`, and
    appends its record to the data folder `data`; None, and nothing appended, for a headless
    session or a Transcript it can't read."""
    r = _count(session, transcript, root)
    if r is None:
        return None
    _append(os.path.join(_folder(data), SESSIONS), r)
    return r


def _count(session: str, transcript: str, root: str) -> Optional[Dict[str, Any]]:
    """The record of the session `session`: names, paths of `.about/` files, ids and numbers only."""
    try:
        with open(transcript, "rb") as f:
            text = f.read()
    except OSError:
        return None
    facts = condense.facts(text)
    if facts.headless:
        return None
    # A subagent's Reads count as the session's own (PRD index).
    reads = list(facts.reads)
    for sub in glob.glob(os.path.join(transcript[: -len(".jsonl")], "subagents", "*.jsonl")):
        try:
            with open(sub, "rb") as f:
                reads += condense.facts(f.read()).reads
        except OSError:
            pass
    return {
        "session": session,
        "start": facts.start,
        "repo": review.repo(root),
        "root": root,
        "transcript": transcript,
        "version": version.read(),
        "denials": [
            {"id": d.id, "check": d.check, "followed": d.followed} for d in facts.denials
        ],
        "skills": sorted({s for s in facts.skills if s.split(":", 1)[0] in _PLUGINS}),
        "index": _index(root, reads, facts.edits),
        "session_start": facts.session_start,
    }


def _index(root: str, reads: List[Tuple[int, str]], edits: List[Tuple[int, str]]) -> Dict[str, int]:
    """Of the edits to a file an ADR or PRD of the repo at `root` names, how many there were and
    before how many one of those was read (PRD index): it names the file's path, or a path of two
    or more segments its path or its folder's ends in."""
    docs: Dict[str, List[str]] = {}
    for folder in _KNOWLEDGE:
        for path in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    docs[os.path.realpath(path)] = _PATH.findall(f.read())
            except OSError:
                pass
    got = {"edits": 0, "read_before": 0}
    for t, path in edits:
        rel = _relative(root, path)
        if rel is None or rel.startswith(".about/"):
            continue
        naming = [doc for doc, paths in docs.items() if any(_names(p, rel) for p in paths)]
        if not naming:
            continue
        got["edits"] += 1
        if any(rt < t and os.path.realpath(_absolute(root, rp)) in naming for rt, rp in reads):
            got["read_before"] += 1
    return got


def _names(path: str, rel: str) -> bool:
    """Whether `path`, found in an ADR's or a PRD's text, names the repo's file `rel`."""
    folder = os.path.dirname(rel)
    for whole in (rel, folder):
        if whole and (whole == path or whole.endswith("/" + path)):
            return True
    return False


def _relative(root: str, path: str) -> Optional[str]:
    """`path` from the repo's root `root`, or None outside it."""
    rel = os.path.relpath(os.path.realpath(_absolute(root, path)), os.path.realpath(root))
    return None if rel.startswith("..") else rel.replace(os.sep, "/")


def _absolute(root: str, path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(root, path)


def _append(file: str, value: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(file), mode=0o700, exist_ok=True)
    fd = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def _jsonl(file: str) -> List[Dict[str, Any]]:
    out = []
    try:
        with open(file, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict):
                    out.append(value)
    except OSError:
        pass
    return out


def records(data: str) -> List[Dict[str, Any]]:
    """Every session's record, its last where it was counted more than once (a resumed session)."""
    by: Dict[str, Dict[str, Any]] = {}
    for r in _jsonl(os.path.join(_folder(data), SESSIONS)):
        if isinstance(r.get("session"), str):
            by[r["session"]] = r
    return list(by.values())


def labels(data: str) -> Dict[str, str]:
    """The maintainer's label of each denial, by `<session> <call id>`: its last."""
    got = {}
    for v in _jsonl(os.path.join(_folder(data), LABELS)):
        if v.get("label") in (REAL, FALSE):
            got[f"{v.get('session')} {v.get('id')}"] = v["label"]
    return got


def label(data: str, session: str, id: str, value: str) -> str:
    """Labels the denial of the call `id` in the session `session` real or false; the reason it
    can't, or ""."""
    if value not in (REAL, FALSE):
        return f"the label is {REAL} or {FALSE}, not {value}"
    for r in records(data):
        if r.get("session") == session and any(d.get("id") == id for d in r.get("denials", [])):
            _append(os.path.join(_folder(data), LABELS), {"session": session, "id": id, "label": value})
            return ""
    return f"no denial of the call {id} in the session {session}"


def backfill(data: str, config: str) -> int:
    """Counts, once, the sessions in a repo whose Transcripts were on disk in Claude Code's config
    folder `config` before the first report; how many it counted."""
    mark = os.path.join(_folder(data), BACKFILLED)
    if os.path.exists(mark):
        return 0
    known = {r.get("session") for r in records(data)}
    n = 0
    for transcript in glob.glob(os.path.join(config, "projects", "*", "*.jsonl")):
        session = os.path.basename(transcript)[: -len(".jsonl")]
        if session in known:
            continue
        root = repo.root(condense.cwd(transcript))
        if root and not _own(root, config) and record(data, session, transcript, root):
            n += 1
    os.makedirs(_folder(data), mode=0o700, exist_ok=True)
    with open(mark, "w", encoding="utf-8") as f:
        f.write(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    return n


def _own(root: str, config: str) -> bool:
    """Whether `root` is the home folder or Claude Code's own, where no session is counted."""
    home = os.path.expanduser("~")
    return root in (home, config) or root.startswith(config.rstrip("/") + "/")


@dataclass
class _Window:
    """The figures of one window of days."""

    sessions: int = 0
    repos: set = field(default_factory=set)
    denials: Dict[str, Dict[str, int]] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)
    edits: int = 0
    read_before: int = 0
    starts: Dict[str, List[int]] = field(default_factory=dict)


def _tally(rs: List[Dict[str, Any]], marks: Dict[str, str]) -> _Window:
    w = _Window()
    for r in rs:
        w.sessions += 1
        w.repos.add(r.get("repo", ""))
        for d in r.get("denials", []):
            c = w.denials.setdefault(d.get("check", "?"), {})
            for key in ("all", d.get("followed", "?"), marks.get(f"{r['session']} {d.get('id')}", "unlabeled")):
                c[key] = c.get(key, 0) + 1
        for s in r.get("skills", []):
            w.skills[s] = w.skills.get(s, 0) + 1
        index = r.get("index", {})
        w.edits += index.get("edits", 0)
        w.read_before += index.get("read_before", 0)
        for p, n in r.get("session_start", {}).items():
            w.starts.setdefault(p, []).append(n)
    return w


def _day(r: Dict[str, Any]) -> str:
    return str(r.get("start", ""))[:10]


def report(data: str, days: int, only: str, now: datetime, evals: str) -> str:
    """The report over the last `days` days before `now`, the window before it beside each figure,
    of every repo or those whose name holds `only`; with the eval suites of the repo at `evals`,
    where it has `evals/` (PRD assessment)."""
    rs = [r for r in records(data) if only in r.get("repo", "")]
    since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    before = (now - timedelta(days=2 * days)).strftime("%Y-%m-%d")
    marks = labels(data)
    cur = _tally([r for r in rs if _day(r) >= since], marks)
    old = _tally([r for r in rs if before <= _day(r) < since], marks)
    out = [
        f"{names.PLUGIN} assessment: the last {days} days, from {since}; (in brackets) the {days} "
        "before",
        f"Sessions counted (PRD assessment): {cur.sessions} ({old.sessions}), in "
        f"{len(cur.repos)} repo(s)",
        "",
        "Checks' denials (ADR checks, ADR measurement):",
    ]
    for check in sorted(set(cur.denials) | set(old.denials)):
        c, o = cur.denials.get(check, {}), old.denials.get(check, {})
        parts = [f"{k} {c.get(k, 0)}" for k in ("another-way", "went-on", "nothing")]
        parts += [f"{k} {c.get(k, 0)}" for k in (REAL, FALSE, "unlabeled")]
        out.append(f"  {check}: {c.get('all', 0)} ({o.get('all', 0)}): " + ", ".join(parts))
    if not cur.denials and not old.denials:
        out.append("  none")
    out += ["", "Skills loaded, sessions (ADR evals):"]
    for s in sorted(set(cur.skills) | set(old.skills), key=lambda s: (-cur.skills.get(s, 0), s)):
        out.append(f"  {s}: {cur.skills.get(s, 0)} ({old.skills.get(s, 0)})")
    if not cur.skills and not old.skills:
        out.append("  none")
    out += [
        "",
        "PRD index: edits to a file an ADR or PRD names, after a read of it: "
        f"{cur.read_before} of {cur.edits} ({old.read_before} of {old.edits})",
        "",
        "Session start, characters a session (PRD index, ADR guidelines):",
    ]
    for p in sorted(set(cur.starts) | set(old.starts)):
        out.append(f"  {p}: {_mean(cur.starts.get(p, []))} ({_mean(old.starts.get(p, []))})")
    if not cur.starts and not old.starts:
        out.append("  none")
    out += [""] + _reviews(data, rs, since, before, now)
    stale = _evals(evals)
    if stale is not None:
        out += ["", "Eval suites whose skill changed after their latest result (ADR evals):"]
        out += [f"  {line}" for line in stale] or ["  none"]
    out += [""] + _unlabeled(rs, marks)
    return condense.mask("\n".join(out))


def _mean(ns: List[int]) -> int:
    return sum(ns) // len(ns) if ns else 0


def _reviews(data: str, rs: List[Dict[str, Any]], since: str, before: str, now: datetime) -> List[str]:
    """The Session reviews' figures (PRD session-review, PRD visibility): the decisions on their
    Proposals, those adding to an Inbox, and the longest any Proposal waits."""
    repos = {r.get("repo", "") for r in rs}
    cur: Dict[str, int] = {}
    old: Dict[str, int] = {}
    for d in review.log(data):
        if d.repo not in repos:
            continue
        w = cur if d.at[:10] >= since else old if d.at[:10] >= before else None
        if w is None:
            continue
        accepted = d.decision in (review.ACCEPTED, review.ACCEPTED_EDITED)
        decision = "accepted" if accepted else d.decision
        w[decision] = w.get(decision, 0) + 1
        if d.target == "inbox" and d.kind == "add" and accepted:
            w["inbox"] = w.get("inbox", 0) + 1
    out = ["Session review (PRD session-review):"]
    for key in ("accepted", review.REJECTED, review.DEFERRED):
        out.append(f"  {key}: {cur.get(key, 0)} ({old.get(key, 0)})")
    out.append(f"  Inbox items added: {cur.get('inbox', 0)} ({old.get('inbox', 0)})")
    longest, where, waiting = 0.0, "", 0
    for root in sorted({r.get("root", "") for r in rs if r.get("root")}):
        for it in review.items(root, data):
            if not it.pending:
                continue
            waiting += 1
            try:
                made = datetime.strptime(it.review[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            age = (now - made).total_seconds() / 86400
            if age > longest:
                longest, where = age, os.path.basename(root)
    out.append(
        f"Proposals waiting (PRD visibility): {waiting}"
        + (f", the longest {int(longest)} days, in {where}" if waiting and where else "")
    )
    return out


def _evals(root: str) -> Optional[List[str]]:
    """Of the repo at `root` with `evals/`, each suite whose skill's text changed in a commit after
    the suite's latest result, with that result; None without `evals/`."""
    if not root or not os.path.isdir(os.path.join(root, "evals")):
        return None
    latest: Dict[str, Tuple[str, Any, Any]] = {}
    for path in glob.glob(os.path.join(root, "evals", "results", "*", "aggregate-result.json")):
        try:
            with open(path, encoding="utf-8") as f:
                result = json.load(f)
        except (OSError, ValueError):
            continue
        at = result.get("startedAt") if isinstance(result, dict) else None
        if not isinstance(at, str):
            continue
        for case in result.get("cases", []):
            parts = str(case.get("dir", "")).split("/")
            if len(parts) < 2:
                continue
            agg = case.get("aggregates") or {}
            if parts[1] not in latest or at > latest[parts[1]][0]:
                latest[parts[1]] = (at, agg.get("score"), agg.get("delta"))
    out = []
    for suite in sorted(e for e in os.listdir(os.path.join(root, "evals")) if e != "results"):
        skills = glob.glob(os.path.join(root, "plugins", "*", "skills", suite))
        if not os.path.isdir(os.path.join(root, "evals", suite)) or not skills:
            continue
        changed = _changed(root, os.path.relpath(skills[0], root))
        at, score, delta = latest.get(suite, ("", None, None))
        if not at:
            out.append(f"{suite}: no result")
        elif changed and changed > at:
            out.append(f"{suite}: changed {changed[:10]}, latest result {at[:10]}, score {score}, "
                       f"delta {delta}")
    return out


def _changed(root: str, path: str) -> str:
    """When the last commit changing `path` in the repo at `root` was made, UTC, ISO 8601."""
    try:
        p = subprocess.run(["git", "-C", root, "log", "-1", "--format=%cI", "--", path],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return ""
    s = p.stdout.strip()
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return ""


def _unlabeled(rs: List[Dict[str, Any]], marks: Dict[str, str]) -> List[str]:
    """The denials not labeled yet whose Transcript is still there, each with its call as
    `condense` masks it, for the maintainer to label."""
    out = []
    for r in sorted(rs, key=_day):
        todo = [d for d in r.get("denials", []) if f"{r['session']} {d.get('id')}" not in marks]
        if not todo:
            continue
        try:
            with open(r.get("transcript", ""), "rb") as f:
                calls = {d.id: d.call for d in condense.facts(f.read()).denials}
        except OSError:
            continue
        for d in todo:
            call = calls.get(d.get("id"), "?")
            out.append(f"  {r['session']} {d.get('id')} {d.get('check')}: {call}")
    if not out:
        return ["Denials to label (ADR checks): none"]
    return [f"Denials to label (ADR checks), with /{names.PLUGIN}:assess:"] + out
