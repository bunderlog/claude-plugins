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
# The figures a Release added after the first records, each a field of a record; a mark per
# figure, `recounted-<figure>`, says the records without it were counted again (PRD assessment).
ADDED = ("hathi", "guidelines", "workflows")
RECOUNTED = "recounted-"

REAL, FALSE = "real", "false"
# bunderlog's plugins, whose skills a record counts.
_PLUGINS = (names.PLUGIN, names.KNOWLEDGE, names.BUILD)
DAYS = 30

# The folders of a repo's ADRs and PRDs, whose files name the code they rest on (PRD index).
_KNOWLEDGE = (names.ADRS, names.PRDS)
# A path of two or more segments in an ADR's or a PRD's text.
_PATH = re.compile(r"[\w.@-]+(?:/[\w.@-]+)+")

# The Guidelines a file of their kind gives, each telling whether a path is one, as louie's Hook
# tells them apart (ADR guidelines); copied, since the plugins share no code (ADR plugin).
_AGENT_FILES = ("SKILL.md", "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md")
_AGENT_FOLDERS = ("agents", "commands", "skills")


def _for_agents(path: str) -> bool:
    parts = path.replace(os.sep, "/").split("/")
    if parts[-1] in _AGENT_FILES:
        return True
    return parts[-1].endswith(".md") and any(
        a == ".claude" and b in _AGENT_FOLDERS for a, b in zip(parts, parts[1:])
    )


_BY_KIND = {
    "go": lambda path: os.path.splitext(path)[1] == ".go",
    "typescript": lambda path: os.path.splitext(path)[1] in (".ts", ".tsx", ".mts", ".cts", ".vue"),
    "vue": lambda path: os.path.splitext(path)[1] == ".vue",
    "writing-for-agents": _for_agents,
}
# A Guideline's file in louie's `guidelines/`, which Claude read.
_GUIDELINE_FILE = re.compile(r"/" + names.BUILD + r"/(?:.+/)?guidelines/([a-z0-9-]+)\.md$")


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
    folder = transcript[: -len(".jsonl")]
    for sub in glob.glob(os.path.join(folder, "subagents", "*.jsonl")):
        try:
            with open(sub, "rb") as f:
                reads += condense.facts(f.read()).reads
        except OSError:
            pass
    # The commits and pushes of a Workflow's agents count as the session's, each agent's failures
    # fixed only in its own order (PRD assessment).
    hathi = list(facts.hathi)
    for sub in sorted(glob.glob(os.path.join(folder, "subagents", "workflows", "*", "agent-*.jsonl"))):
        try:
            with open(sub, "rb") as f:
                hathi += condense.facts(f.read()).hathi
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
        "hathi": [{"check": h.check, "followed": h.followed} for h in hathi],
        "guidelines": _guidelines(facts.guidelines, facts.reads, facts.edits),
        "workflows": [{"name": n, "end": end} for n, end in facts.workflows],
    }


def _guidelines(
    given: List[Tuple[int, str]], reads: List[Tuple[int, str]], edits: List[Tuple[int, str]]
) -> Dict[str, str]:
    """Each Guideline in the session's context, given by louie's Hook (`given`) or its file read,
    and each a file of whose kind the session edited: for one of those, whether it came before or
    after the first edit of its kind, or never; for the rest, in (ADR guidelines)."""
    came: Dict[str, int] = {}
    files = [(t, _GUIDELINE_FILE.search(path.replace(os.sep, "/"))) for t, path in reads]
    for t, name in given + [(t, m.group(1)) for t, m in files if m]:
        came[name] = min(t, came.get(name, t))
    out: Dict[str, str] = {}
    for name, kind in _BY_KIND.items():
        first = min((t for t, path in edits if kind(path)), default=None)
        if first is None:
            continue
        if name not in came:
            out[name] = "never"
        else:
            out[name] = "before" if came[name] < first else "after"
    for name in came:
        out.setdefault(name, "in")
    return out


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
        # The project's knowledge is no code, a worktree's own `.about/` neither.
        if rel is None or rel.startswith(".about/") or "/.about/" in rel:
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


def recount(data: str) -> int:
    """Counts again, once for each figure a Release added, every record without it whose
    Transcript is still on disk, appending a new record for it; how many it counted."""
    folder = _folder(data)
    todo = [f for f in ADDED if not os.path.exists(os.path.join(folder, RECOUNTED + f))]
    if not todo:
        return 0
    n = 0
    for r in records(data):
        if all(f in r for f in todo):
            continue
        transcript, root = r.get("transcript"), r.get("root")
        if not isinstance(transcript, str) or not isinstance(root, str):
            continue
        if os.path.isfile(transcript) and record(data, r["session"], transcript, root):
            n += 1
    os.makedirs(folder, mode=0o700, exist_ok=True)
    for f in todo:
        with open(os.path.join(folder, RECOUNTED + f), "w", encoding="utf-8") as out:
            out.write(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    return n


def _own(root: str, config: str) -> bool:
    """Whether `root` is the home folder or Claude Code's own, where no session is counted."""
    home = os.path.expanduser("~")
    return root in (home, config) or root.startswith(config.rstrip("/") + "/")


@dataclass
class _Window:
    """The figures of one window of days; of a figure a Release added, `covered` counts the
    sessions whose record has it."""

    sessions: int = 0
    repos: set = field(default_factory=set)
    denials: Dict[str, Dict[str, int]] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)
    edits: int = 0
    read_before: int = 0
    starts: Dict[str, List[int]] = field(default_factory=dict)
    covered: Dict[str, int] = field(default_factory=dict)
    hathi: Dict[str, Dict[str, int]] = field(default_factory=dict)
    guidelines: Dict[str, Dict[str, int]] = field(default_factory=dict)
    workflows: Dict[str, Dict[str, int]] = field(default_factory=dict)


# How a Workflow's task-notification ends it, by its status; any other status stopped it.
_ENDS = {"completed": "completed", "failed": "failed", "": "no end"}


def _add(counts: Dict[str, Dict[str, int]], name: str, *keys: str) -> None:
    c = counts.setdefault(name, {})
    for key in keys:
        c[key] = c.get(key, 0) + 1


def _tally(rs: List[Dict[str, Any]], marks: Dict[str, str]) -> _Window:
    w = _Window()
    for r in rs:
        w.sessions += 1
        w.repos.add(r.get("repo", ""))
        for d in r.get("denials", []):
            mark = marks.get(f"{r['session']} {d.get('id')}", "unlabeled")
            _add(w.denials, d.get("check", "?"), "all", d.get("followed", "?"), mark)
        for s in r.get("skills", []):
            w.skills[s] = w.skills.get(s, 0) + 1
        index = r.get("index", {})
        w.edits += index.get("edits", 0)
        w.read_before += index.get("read_before", 0)
        for p, n in r.get("session_start", {}).items():
            w.starts.setdefault(p, []).append(n)
        for figure in ADDED:
            if figure in r:
                w.covered[figure] = w.covered.get(figure, 0) + 1
        for h in r.get("hathi", []):
            _add(w.hathi, h.get("check", "?"), "all", h.get("followed", "?"))
        # A Guideline's sessions in the context, and of those editing a file of its kind, the
        # sessions it came before the first such edit in.
        for name, outcome in r.get("guidelines", {}).items():
            keys = [] if outcome == "never" else ["in"]
            keys += [] if outcome == "in" else ["edited"]
            keys += ["before"] if outcome == "before" else []
            _add(w.guidelines, name, *keys)
        for run in r.get("workflows", []):
            _add(w.workflows, run.get("name", "?"), "all", _ENDS.get(run.get("end", ""), "stopped"))
    return w


def _day(r: Dict[str, Any]) -> str:
    return str(r.get("start", ""))[:10]


def report(data: str, days: int, only: str, now: datetime, evals: str) -> str:
    """The report over the last `days` days before `now`, the window before it beside each figure,
    of every repo or those whose name holds `only`; with the eval suites of the repo at `evals`,
    where it has `evals/` (PRD assessment). Its figures stand under whose part each counts: the
    plugins baloo, louie and bagheera, then `hathi`'s Checks."""
    rs = [r for r in records(data) if only in r.get("repo", "")]
    since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    before = (now - timedelta(days=2 * days)).strftime("%Y-%m-%d")
    marks = labels(data)
    cur = _tally([r for r in rs if _day(r) >= since], marks)
    old = _tally([r for r in rs if before <= _day(r) < since], marks)
    stale = _evals(evals)
    out = [
        f"{names.MARKETPLACE} assessment: the last {days} days, from {since}; (in brackets) the "
        f"{days} before",
        f"Sessions counted (PRD assessment): {cur.sessions} ({old.sessions}), in "
        f"{len(cur.repos)} repo(s)",
    ]
    other = "other"
    if other in cur.starts or other in old.starts:
        out += ["", "Session start of no plugin's, characters a session (PRD index): "
                f"{_mean(cur.starts.get(other, []))} ({_mean(old.starts.get(other, []))})"]
    if stale:
        out += _stale([line for p, line in stale if p not in _PLUGINS])

    out += ["", names.KNOWLEDGE] + _skills(cur, old, names.KNOWLEDGE)
    out += [
        "",
        "PRD index: edits to a file an ADR or PRD names, after a read of it: "
        f"{cur.read_before} of {cur.edits} ({old.read_before} of {old.edits})",
    ]
    out += _start(cur, old, names.KNOWLEDGE) + _stale_of(stale, names.KNOWLEDGE)

    out += ["", names.BUILD] + _skills(cur, old, names.BUILD)
    out += ["", f"Guidelines in the context, sessions (ADR guidelines), {_over(cur, old, 'guidelines')}:"]
    for g in sorted(set(cur.guidelines) | set(old.guidelines)):
        c, o = cur.guidelines.get(g, {}), old.guidelines.get(g, {})
        text = f"  {g}: {c.get('in', 0)} ({o.get('in', 0)})"
        if g in _BY_KIND:
            text += (f", before the first edit of its files {c.get('before', 0)} of "
                     f"{c.get('edited', 0)} ({o.get('before', 0)} of {o.get('edited', 0)})")
        out.append(text)
    if not cur.guidelines and not old.guidelines:
        out.append("  none")
    out += ["", f"Workflows run (PRD delivery, ADR verify), {_over(cur, old, 'workflows')}:"]
    out += _counts(cur.workflows, old.workflows, ("completed", "failed", "stopped", "no end"))
    out += _start(cur, old, names.BUILD) + _stale_of(stale, names.BUILD)

    out += ["", names.PLUGIN] + _skills(cur, old, names.PLUGIN)
    out += ["", "Checks' denials (ADR checks, ADR measurement):"]
    out += _counts(cur.denials, old.denials,
                   ("another-way", "went-on", "nothing", REAL, FALSE, "unlabeled"))
    out += [""] + _reviews(data, rs, since, before, now)
    out += _start(cur, old, names.PLUGIN) + _stale_of(stale, names.PLUGIN)
    out += [""] + _unlabeled(rs, marks)

    out += ["", names.HATHI]
    out += ["", f"Git hooks' failures (ADR git-hooks, ADR measurement), {_over(cur, old, 'hathi')}:"]
    out += _counts(cur.hathi, old.hathi, ("fixed", "nothing"))
    return condense.mask("\n".join(out))


def _counts(cur: Dict[str, Dict[str, int]], old: Dict[str, Dict[str, int]],
            keys: Tuple[str, ...]) -> List[str]:
    """A line for each name in `cur` or `old`: how many in each window, and in `cur` of each key."""
    out = []
    for name in sorted(set(cur) | set(old)):
        c, o = cur.get(name, {}), old.get(name, {})
        parts = ", ".join(f"{k} {c.get(k, 0)}" for k in keys)
        out.append(f"  {name}: {c.get('all', 0)} ({o.get('all', 0)}): {parts}")
    return out or ["  none"]


def _over(cur: _Window, old: _Window, figure: str) -> str:
    """How many sessions a figure a Release added covers, in each window."""
    n = cur.covered.get(figure, 0)
    return f"over {n} session{'' if n == 1 else 's'} ({old.covered.get(figure, 0)})"


def _skills(cur: _Window, old: _Window, plugin: str) -> List[str]:
    """The skills of `plugin` loaded, sessions, the most loaded first."""
    out = ["", "Skills loaded, sessions (ADR evals):"]
    mine = [s for s in set(cur.skills) | set(old.skills) if s.split(":", 1)[0] == plugin]
    for s in sorted(mine, key=lambda s: (-cur.skills.get(s, 0), s)):
        out.append(f"  {s}: {cur.skills.get(s, 0)} ({old.skills.get(s, 0)})")
    return out + ([] if mine else ["  none"])


def _start(cur: _Window, old: _Window, plugin: str) -> List[str]:
    return [
        "",
        "Session start, characters a session (PRD index, ADR guidelines):",
        f"  {plugin}: {_mean(cur.starts.get(plugin, []))} ({_mean(old.starts.get(plugin, []))})",
    ]


def _stale_of(stale: Optional[List[Tuple[str, str]]], plugin: str) -> List[str]:
    """The eval suites of `plugin`'s skills that are stale; nothing where the repo has no evals."""
    if stale is None:
        return []
    return _stale([line for p, line in stale if p == plugin]) or [
        "", "Eval suites whose skill changed after their latest result (ADR evals): none"]


def _stale(lines: List[str]) -> List[str]:
    if not lines:
        return []
    return ["", "Eval suites whose skill changed after their latest result (ADR evals):"] + [
        f"  {line}" for line in lines]


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


def _evals(root: str) -> Optional[List[Tuple[str, str]]]:
    """Of the repo at `root` with `evals/`, each suite whose skill's text changed in a commit after
    the suite's latest result, with that result, beside the plugin whose skill it is; None without
    `evals/`."""
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
    out: List[Tuple[str, str]] = []
    for suite in sorted(e for e in os.listdir(os.path.join(root, "evals")) if e != "results"):
        skills = glob.glob(os.path.join(root, "plugins", "*", "skills", suite))
        if not os.path.isdir(os.path.join(root, "evals", suite)) or not skills:
            continue
        skill = os.path.relpath(skills[0], root)
        plugin = skill.replace(os.sep, "/").split("/")[1]
        changed = _changed(root, skill)
        at, score, delta = latest.get(suite, ("", None, None))
        if not at:
            out.append((plugin, f"{suite}: no result"))
        elif changed and changed > at:
            out.append((plugin, f"{suite}: changed {changed[:10]}, latest result {at[:10]}, "
                                f"score {score}, delta {delta}"))
    return out


def _changed(root: str, path: str) -> str:
    """When the last commit changing `path` in the repo at `root` was made, UTC, ISO 8601."""
    try:
        p = subprocess.run(["git", "-C", root, "log", "-1", "--format=%ct", "--", path],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return ""
    try:
        at = datetime.fromtimestamp(int(p.stdout.strip()), timezone.utc)
        return at.strftime("%Y-%m-%dT%H:%M:%S")
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
