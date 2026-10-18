"""Starts the Session review of a session that ended, which writes its Proposals to
.about/proposals/<review>.md, and keeps what the user decides of each (ADR session-review)."""

# cspell:ignore dont

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlsplit, urlunsplit

from baloo import condense, names, settings

# Set in a Session review's environment, so that its own end starts no review.
ENV = names.PLUGIN.upper() + "_SESSION_REVIEW"

_MIN_CHARS = 2_000  # a shorter conversation can't have settled a term or a decision
_MAX_CHARS = 200_000  # of a longer one, the review reads the end
_KEPT = 7 * 24 * 3600
_SHOWN = 50  # the most rejected Proposals a review is told of

# What a review may spend, in US dollars, as `claude -p --max-budget-usd` counts it: about three
# times the dearest of 40 reviews up to 2026-10-17, about $0.81 at Claude Opus 5.5's prices, so a
# dearer default model fits too. A review that reaches it fails, and is told so.
_BUDGET = "3"

# The line between what an earlier review of a resumed session read and what it didn't.
_SEAM = "----- reviewed before: above this line only for context -----"


class Error(Exception):
    """Why a decision can't be logged."""


def headless() -> bool:
    """Whether this process runs in a headless session, such as `claude -p` run by a project's own
    Git hook. Nobody there can answer, so it is shown no Proposal."""
    return condense.headless(os.environ.get("CLAUDE_CODE_ENTRYPOINT", ""))


def _prompt(id: str, file: str, rejected: List[str], earlier: bool) -> str:
    """What the review of `id` is asked: to write its Proposals to `file`, given the Proposals the
    user rejected before, and whether an earlier review read the conversation's start."""
    p = names.PLUGIN
    before = ""
    if earlier:
        before += (
            f'An earlier review read the conversation down to the line "{_SEAM}": propose only '
            "from what follows it.\n"
        )
    if rejected:
        before += (
            "The user rejected these proposals before; propose none of them again:\n- "
            + "\n- ".join(rejected)
            + "\n"
        )
    return (
        """The conversation that just ended is on stdin. Find what it settled or left open that
.about/ doesn't say yet, and propose each change to .about/ in """
        + file
        + """; edit nothing else, and
never .about/ itself: the user accepts, rejects or defers each proposal later. Use the """
        + p
        + ":glossary and "
        + p
        + """:adr skills for what to check and for the
format of a term or an ADR, but write their result as a proposal. Nobody can answer questions:
propose only what the conversation clearly agreed, and only about this repo. Anything contested or
left open, and a bug or problem it found but didn't fix, is an Inbox item to add to """
        + names.INBOX
        + """: a "## <title>", a line "<YYYY-MM-DD> · session review", then what it is and
what would settle it. What is still to do or check on a ticket the conversation worked on (a check
on a device, a PR to merge, a wait on firmware) stays with that ticket: propose nothing for it. An
item the conversation settled is one to delete. A PRD changes only where
the conversation agreed what the feature is for or how it is checked. Propose nothing already
waiting in """
        + names.PROPOSALS
        + """.
"""
        + before
        + """
Write nothing when there is nothing to propose. Otherwise write the file as:

# Session review """
        + id
        + """

## P1 · <target> · <kind> · <path> · <title>

Why: <one line: what in the conversation it comes from>

Before:
~~~markdown
<the text it changes or deletes, copied exactly from the file>
~~~

After:
~~~markdown
<the text it adds, or the text that replaces Before>
~~~

Number them P1, P2… <target> is inbox, glossary, adr or prd, and <path> its file:
"""
        + names.INBOX
        + ", "
        + names.GLOSSARY
        + ", "
        + names.ADRS
        + "<subject>.md or "
        + names.PRDS
        + """<feature>.md. <kind> is add (After only: the new text, a new file's whole text), edit
(Before and After) or delete (Before only). Keep each Before short but unique in its file. End your
reply with one line per proposal."""
    )


def _folder(root: str, data: str) -> str:
    """Where the reviews of the repo at `root` keep their files in the plugin's data folder `data`:
    per review, its reply, its process id while it runs and what it wrote to stderr."""
    digest = hashlib.sha256(root.encode()).hexdigest()[:16]
    return os.path.join(data, "session-review", digest)


def review_id(at: datetime, session: str) -> str:
    """The id of a review started at `at` of the session `session`: sorted by when it started."""
    return at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + session[:8]


def start(
    claude: str, plugin: str, root: str, data: str, session: str, transcript: Union[str, bytes]
) -> bool:
    """Starts the Session review of the session `session`, whose Transcript is `transcript`, with
    the `claude` given and the plugin in the folder `plugin`, whose skills it uses, at the repo's
    root `root`, keeping its files in the plugin's data folder `data`.
    It returns once the review runs, detached, and says whether one started: none does for a
    headless session, or one too short to have settled much. Of a resumed session, it reads only
    what an earlier review didn't, with what that one read before it for context. What fails raises
    OSError."""
    if condense.condense(transcript, "").headless:
        return False
    folder = _folder(root, data)
    to = transcript.rfind(b"\n" if isinstance(transcript, bytes) else "\n") + 1
    at = _from(folder, session, to)
    added = condense.conversation(transcript[at:to], len(transcript))
    if len(added) < _MIN_CHARS:
        return False
    read = min(len(added), _MAX_CHARS)
    conversation = added[len(added) - read :]
    earlier = condense.conversation(transcript[:at], _MAX_CHARS - read) if at else ""
    if earlier:
        conversation = earlier + "\n\n" + _SEAM + "\n\n" + conversation
    os.makedirs(folder, mode=0o700, exist_ok=True)
    # The Proposals are the user's to decide, not to commit by accident with the rest.
    settings.exclude(root, os.path.join(root, names.PROPOSALS))
    fd, name = tempfile.mkstemp(prefix="conversation-", dir=folder)
    try:
        with os.fdopen(fd, "w+", encoding="utf-8") as stdin:
            stdin.write(conversation)
            stdin.seek(0)
            id = review_id(datetime.now(timezone.utc), session)
            base = os.path.join(folder, id)
            with _create(base + ".txt") as out, _create(base + ".err") as errs:
                # Only reading, and writing its own Proposals; anything not allowed is denied
                # rather than asked. An Edit rule covers writing a file too.
                # The plugin is loaded from its folder too, since the session that ended may have
                # had it from somewhere the review's doesn't, such as --plugin-dir.
                file = "./" + names.PROPOSALS + id + ".md"
                cmd = [
                    claude, "-p", _prompt(id, file, _rejected(root, data, _SHOWN), bool(earlier)),
                    "--plugin-dir", plugin, "--output-format", "json", "--max-budget-usd", _BUDGET,
                    "--tools", "Read,Glob,Grep,Edit,Write,Skill", "--permission-mode", "dontAsk",
                    "--allowedTools", "Read", "Glob", "Grep", "Skill",
                    "Edit(./" + names.PROPOSALS + "**)",
                ]
                proc = subprocess.Popen(
                    cmd,
                    cwd=root,
                    env={**os.environ, ENV: "1"},
                    stdin=stdin,
                    stdout=out,
                    stderr=errs,
                    start_new_session=True,  # outlives Claude Code's exit
                )
    finally:
        os.remove(name)  # the review keeps its open file
    try:
        _write(base + ".pid", str(proc.pid))
    except OSError:
        pass
    # Reaps it should this process outlive it, as a test's does.
    threading.Thread(target=proc.wait, daemon=True).start()
    _mark(folder, session, id, at, to)
    _log_run(data, repo(root), id, "started", "", f"read {read} of {len(added)} characters")
    return True


def _create(path: str):
    return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w")


def _write(path: str, text: str) -> None:
    with _create(path) as f:
        f.write(text)


def running(root: str, data: str) -> bool:
    """Whether a Session review of the repo at `root` still runs. It also deletes the files of
    reviews that ended more than a week ago, with where they stopped reading their session, and
    those Releases before reviews had ids kept, one per repo."""
    reviews = os.path.join(data, "session-review")
    for name in _names(reviews):
        if re.fullmatch(r"[^/]{16}\.txt.*", name, re.S):
            _remove(os.path.join(reviews, name))
    folder = _folder(root, data)
    is_running = False
    for name in _names(folder):
        if not name.endswith(".pid"):
            continue
        pid = os.path.join(folder, name)
        try:
            with open(pid, encoding="utf-8") as f:
                n: Optional[int] = int(f.read().strip())
        except (OSError, ValueError):
            n = None
        if n is not None and _alive(n):
            is_running = True
            continue
        try:
            old = time.time() - os.stat(pid).st_mtime > _KEPT
        except OSError:
            old = False
        if old:
            base = pid[: -len(".pid")]
            for ext in (".pid", ".txt", ".err"):
                _remove(base + ext)
    _forget(os.path.join(folder, "sessions"))
    return is_running


def _names(folder: str) -> List[str]:
    """The names in `folder`, sorted, hidden ones too; none where it can't be listed."""
    try:
        return sorted(os.listdir(folder))
    except OSError:
        return []


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _alive(pid: int) -> bool:
    """Whether the process `pid` still runs."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# The user's decisions on a Proposal, as the log records them.
ACCEPTED = "accepted"
# Accepted with the text changed as it was applied, in the Proposal's Applied; it counts as
# accepted.
ACCEPTED_EDITED = "accepted-edited"
REJECTED = "rejected"
DEFERRED = "deferred"

# How many times a Proposal can be deferred; then it is accepted or rejected.
_MAX_DEFERRED = 2


@dataclass
class Proposal:
    """One change a Session review proposes to .about/: its review's and its own id, its target
    (inbox, glossary, adr or prd), its kind (add, edit or delete), the file it changes, a title,
    the text it changes and the text it puts there, and the text put there instead where it was
    applied changed, which Claude adds; the review's After stays as it proposed it. `problem` says
    why the file can't be read as a Proposal, or is ""."""

    review: str = ""
    id: str = ""
    target: str = ""
    kind: str = ""
    path: str = ""
    title: str = ""
    before: str = ""
    after: str = ""
    applied: str = ""
    problem: str = ""


def _accepted(d: str) -> bool:
    """Whether the decision `d` accepts the Proposal, as proposed or edited."""
    return d in (ACCEPTED, ACCEPTED_EDITED)


@dataclass
class Item(Proposal):
    """A Proposal with what the user decided of it, from the log, and how it stands with its file:
    `stale` when the text it changes is no longer there, `mismatch` when the log and the file
    disagree."""

    decision: str = ""  # the last one, "" for none
    deferred: int = 0
    stale: bool = False
    mismatch: str = ""

    @property
    def pending(self) -> bool:
        """Whether the item still waits for the user's decision."""
        return self.decision in ("", DEFERRED)


_HEADING = re.compile(r"^## (P\d+) · (\S+) · (\S+) · (\S+) · (.+)$")


def parse(review: str, text: str) -> List[Proposal]:
    """The Proposals of the review `review`, from the text of its file. A block is fenced with ~~~,
    as the review is asked to write it, or with ```, as a reviewer may write it anyway."""
    found: List[Proposal] = []
    block = ""  # the field of the last Proposal the lines go to, "" for none
    fence = ""  # the open block's fence, "" outside one
    for line in text.split("\n"):
        if fence and line == fence:
            fence = ""
        elif fence:
            p = found[-1]
            setattr(p, block, getattr(p, block) + line + "\n")
        elif line.startswith("## "):
            block = ""
            m = _HEADING.match(line)
            if m is None:
                found.append(
                    Proposal(
                        review=review,
                        title=line[len("## ") :],
                        problem="its heading is not ## <id> · <target> · <kind> · <path> · <title>",
                    )
                )
                continue
            found.append(
                Proposal(
                    review=review, id=m[1], target=m[2], kind=m[3], path=m[4], title=m[5]
                )
            )
        elif not found:
            pass
        elif line == "Before:":
            block = "before"
        elif line == "After:":
            block = "after"
        elif line == "Applied:":
            block = "applied"
        elif block and (line.startswith("~~~") or line.startswith("```")):
            fence = line[:3]
    for p in found:
        if not p.problem:
            p.problem = _invalid(p)
    return found


def _invalid(p: Proposal) -> str:
    """Why `p` is not a Proposal the user can decide, or ""."""
    file: Optional[Callable[[str], bool]] = {
        "inbox": lambda path: path == names.INBOX,
        "glossary": lambda path: path == names.GLOSSARY,
        "adr": _within(names.ADRS),
        "prd": _within(names.PRDS),
    }.get(p.target)
    if file is None:
        return "its target is not inbox, glossary, adr or prd"
    if not file(p.path):
        return "its path is not a file of its target"
    if p.kind == "add" and (p.after == "" or p.before != ""):
        return "an add has After and no Before"
    if p.kind == "edit" and (p.after == "" or p.before == ""):
        return "an edit has Before and After"
    if p.kind == "delete" and (p.before == "" or p.after != ""):
        return "a delete has Before and no After"
    if p.kind not in ("add", "edit", "delete"):
        return "its kind is not add, edit or delete"
    if p.kind == "delete" and p.applied != "":
        return "a delete has no Applied"
    return ""


def _within(folder: str) -> Callable[[str], bool]:
    """Whether a path is a Markdown file right in the folder `folder`."""

    def check(path: str) -> bool:
        if not path.startswith(folder):
            return False
        name = path[len(folder) :]
        return name != ".md" and name.endswith(".md") and "/" not in name

    return check


def repo(root: str) -> str:
    """How the log names the repo at `root`, the same on every machine: its origin's URL, without a
    user or password, or its root where it has none."""
    try:
        p = subprocess.run(
            ["git", "-C", root, "remote", "get-url", "origin"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return root
    remote = p.stdout.strip()
    if p.returncode != 0 or not remote:
        return root
    try:
        u = urlsplit(remote)
    except ValueError:
        return remote
    if not u.scheme:  # such as git@github.com:o/r.git, which isn't a URL
        return remote
    netloc = u.netloc.rpartition("@")[2]
    return urlunsplit((u.scheme, netloc, u.path, u.query, u.fragment))


def _log_file(data: str) -> str:
    """The log of the user's decisions, in the plugin's data folder `data`: a line per decision, its
    fields split by tabs: when (UTC), the repo, the review, the Proposal, its target, its kind and
    the decision."""
    return os.path.join(data, "session-review", "session-review.log")


_LOG_FIELDS = 7


def _log_lines(file: str) -> List[str]:
    """The lines of `file`, each without its line ending; none where it can't be read."""
    try:
        with open(file, encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
    except OSError:
        return []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _decisions(data: str, repo: str) -> Dict[str, Tuple[str, int]]:
    """The decisions the log holds for the repo `repo`, by review and Proposal: the last one, and
    how many times it was deferred."""
    got: Dict[str, Tuple[str, int]] = {}
    for line in _log_lines(_log_file(data)):
        field = line.split("\t")
        if len(field) != _LOG_FIELDS or field[1] != repo:
            continue
        key = field[2] + "/" + field[3]
        _, deferred = got.get(key, ("", 0))
        if field[6] == DEFERRED:
            deferred += 1
        got[key] = (field[6], deferred)
    return got


def items(root: str, data: str) -> List[Item]:
    """The Proposals in the repo at `root`, each with what the log says of it and how it stands
    with its file, in the order of their reviews."""
    folder = os.path.join(root, names.PROPOSALS)
    files = [os.path.join(folder, n) for n in _names(folder) if n.endswith(".md")]
    if not files:
        return []
    logged = _decisions(data, repo(root))
    out: List[Item] = []
    for file in files:
        try:
            with open(file, encoding="utf-8", errors="replace", newline="") as f:
                text = f.read()
        except OSError:
            continue
        for p in parse(os.path.basename(file)[: -len(".md")], text):
            decision, deferred = logged.get(p.review + "/" + p.id, ("", 0))
            it = Item(**asdict(p), decision=decision, deferred=deferred)
            if not p.problem:
                _stands(it, _read(os.path.join(root, p.path)))
            out.append(it)
    return out


def _read(path: str) -> str:
    """The text of the file at `path`, "" where it can't be read."""
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            return f.read()
    except OSError:
        return ""


def _stands(it: Item, target: str) -> None:
    """Sets how the item `it` stands with the text `target` of its file."""

    def has(block: str) -> bool:
        return _flat(block) in _flat(target)

    put = it.applied or it.after
    applied = has(put)
    if it.kind == "delete":
        applied = not has(it.before)
    if _accepted(it.decision) and not applied and it.kind == "delete":
        it.mismatch = "accepted, but its Before is still in " + it.path
    elif _accepted(it.decision) and not applied:
        it.mismatch = "accepted, but its " + _block(it) + " is not in " + it.path
    elif it.pending and it.kind != "delete" and applied:
        it.mismatch = "its " + _block(it) + " is in " + it.path + ", but no decision is logged"
    elif it.pending and it.kind != "add" and not has(it.before):
        it.stale = True


def _block(it: Item) -> str:
    """Names the text the item puts in its file: its Applied where it has one."""
    return "Applied" if it.applied else "After"


# White space as Go's strings.Fields splits on it: Unicode's White_Space, which Python's own
# split() widens with \x1c to \x1f.
_SPACES = re.compile(
    "[\t\n\v\f\r \x85\xa0  -     　]+"
)


def _flat(text: str) -> str:
    """`text` with each run of white space one space, so a rewrapped line still matches."""
    return " ".join(w for w in _SPACES.split(text) if w)


def decide(root: str, data: str, review: str, id: str, decision: str) -> str:
    """Logs the user's decision `decision` on the Proposal `id` of the review `review` in the repo
    at `root`, and deletes the review's file once each of its Proposals is decided and in its file
    as decided. It returns what Claude should still do, or "", and raises Error where the decision
    can't be logged: an unknown Proposal, a third deferral, or accepting a stale edit."""
    if not _accepted(decision) and decision not in (REJECTED, DEFERRED):
        raise Error(
            f"{decision} is not {ACCEPTED}, {ACCEPTED_EDITED}, {REJECTED} or {DEFERRED}"
        )
    all_items = items(root, data)
    at = next(
        (i for i, it in enumerate(all_items) if it.review == review and it.id == id), -1
    )
    if at < 0:
        raise Error(f"no proposal {id} in {names.PROPOSALS}{review}.md")
    it = all_items[at]
    if decision == DEFERRED and it.deferred >= _MAX_DEFERRED:
        raise Error(f"{id} was deferred {it.deferred} times already: accept or reject it")
    if decision == ACCEPTED_EDITED and it.applied == "":
        raise Error(
            f"{id} has no Applied block: add one of the text you applied first, or log {ACCEPTED}"
        )
    if _accepted(decision) and it.problem:
        raise Error(f"{id} can't be read ({it.problem}): fix it in its file first, or reject it")
    if _accepted(decision) and it.stale and it.kind != "delete":  # a delete applied looks stale
        raise Error(
            f"{id} is stale, its Before no longer in {it.path}: fix it in its file by hand "
            "first, or reject it"
        )
    _append_log(data, repo(root), it, decision)
    it.decision = decision
    it.mismatch = ""
    _stands(it, _read(os.path.join(root, it.path)))
    _tidy(root, data, review, all_items)
    if it.mismatch:
        return (
            f"{review} {id}: {it.mismatch}: apply it, or add an Applied block of what you applied "
            f"to it and log {ACCEPTED_EDITED}"
        )
    return ""


def _append_log(data: str, repo: str, p: Proposal, decision: str) -> None:
    """Adds the decision `decision` on `p` in the repo `repo` to the log. A log written before it
    had fields is moved aside once, to session-review.log.old, so every line parses."""
    file = _log_file(data)
    os.makedirs(os.path.dirname(file), mode=0o700, exist_ok=True)
    if os.path.exists(file):
        first = _log_lines(file)[:1]
        if first and len(first[0].split("\t")) != _LOG_FIELDS:
            os.rename(file, file + ".old")
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = "\t".join([at, repo, p.review, p.id, p.target, p.kind, decision])
    fd = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _tidy(root: str, data: str, review: str, all_items: List[Item]) -> None:
    """Moves the file of the review `review` out of the repo, into the review's folder in the
    plugin's data folder `data`, decided/, once each of its Proposals in `all_items` is accepted or
    rejected and none disagrees with its file; the repo's folder goes with its last file. It is kept
    there for good, for a later measurement to judge the Proposals by."""
    for it in all_items:
        if it.review == review and (it.pending or it.mismatch):
            return
    decided = os.path.join(_folder(root, data), "decided")
    os.makedirs(decided, mode=0o700, exist_ok=True)
    os.rename(
        os.path.join(root, names.PROPOSALS, review + ".md"), os.path.join(decided, review + ".md")
    )
    try:
        os.rmdir(os.path.join(root, names.PROPOSALS))  # only when empty
    except OSError:
        pass


def show(root: str, data: str, session: str, decide: str) -> List[str]:
    """What to tell Claude of the Proposals waiting in the repo at `root`, and of where the log and
    the files disagree, that the session `session` hasn't been told yet; none when nothing is new.
    `decide` is the command that logs a decision. A headless session is told nothing, and showing
    consumes nothing: a Proposal waits until it is decided. First come the reviews that failed or
    read only part of their session since a session last looked, each told once."""
    if headless():
        return []
    ended = _ended(root, data)
    folder = os.path.join(data, "session-review", "shown")
    _forget(folder)
    seen = os.path.join(folder, session)
    known = _read(seen).split("\n")
    proposals: List[str] = []
    mismatches: List[str] = []
    keys: List[str] = []
    for it in items(root, data):
        key = it.review + "/" + it.id
        if it.mismatch:
            key = "mismatch " + key
            if key not in known:
                mismatches.append(f"  mismatch: {it.review} {it.id}, {it.mismatch}")
                keys.append(key)
        elif it.pending and key not in known:
            proposals.append("  " + _line(it))
            keys.append(key)
    if not keys:
        return ended
    lines: List[str] = ended
    if proposals:
        p = names.PLUGIN
        lines.append(
            "Session review proposals for .about/ wait for the user, in "
            + names.PROPOSALS
            + "<review>.md: show the user this list and ask, for each, accept, reject or defer, "
            "after reading its file for the full edit; recommend reject for a stale one, and "
            "offer no defer for one deferred twice. Apply each accepted one: a glossary, adr or prd "
            "one through the " + p + ":glossary, " + p + ":adr or " + p + ":prd skill, an inbox "
            "one by its edit as written; where what you applied differs from its After, add to "
            "the Proposal an Applied: block of the text you applied, fenced as After is, and log "
            "accepted-edited. Then log each answer with `"
            + decide
            + " <review> <id> accepted|accepted-edited|rejected|deferred`"
        )
        lines.extend(proposals)
    if mismatches:
        lines.append(
            "Session review proposals whose log and file disagree: tell the user, and fix the file "
            "or log the decision"
        )
        lines.extend(mismatches)
    if session:
        try:
            os.makedirs(folder, mode=0o700, exist_ok=True)
            _write(seen, "\n".join(known + keys))
        except OSError:
            pass
    return lines


def _line(it: Item) -> str:
    """The item `it` as Claude is shown it."""
    if it.problem:
        return f"{it.review} {it.id}: can't be read, {it.problem}: {it.title}"
    text = f"{it.review} {it.id} {it.target} {it.kind} {it.path}: {it.title}"
    if it.stale:
        text += " (stale: its Before is no longer in its file)"
    if it.deferred > 0:
        text += f" (deferred {it.deferred}×)"
    return text


def _forget(folder: str) -> None:
    """Deletes what sessions were told more than a week ago."""
    now = time.time()
    for name in _names(folder):
        path = os.path.join(folder, name)
        try:
            if now - os.stat(path).st_mtime > _KEPT:
                os.remove(path)
        except OSError:
            pass


def _runs_file(data: str) -> str:
    """The log of the reviews' runs, in the plugin's data folder `data`: a line an event, its fields
    split by tabs: when (UTC), the repo, the review, the event (started, ok or failed), what it cost
    in US dollars, "" where unknown, and a detail: for started, how much of the conversation it
    read; for failed, why."""
    return os.path.join(data, "session-review", "runs.log")


_RUN_FIELDS = 6


def _log_run(data: str, repo: str, id: str, event: str, cost: str, detail: str) -> None:
    """Adds the event `event` of the review `id` in the repo `repo` to the log of runs."""
    file = _runs_file(data)
    os.makedirs(os.path.dirname(file), mode=0o700, exist_ok=True)
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = "\t".join([at, repo, id, event, cost, _flat(detail)])
    fd = os.open(file, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _runs(data: str, repo: str) -> List[List[str]]:
    """The fields of each line of the log of runs in the repo `repo`."""
    out = []
    for line in _log_lines(_runs_file(data)):
        field = line.split("\t")
        if len(field) == _RUN_FIELDS and field[1] == repo:
            out.append(field)
    return out


def _outcome(folder: str, id: str) -> Tuple[bool, str, str]:
    """How the review `id`, whose files are in `folder`, ended, read from its reply: whether it
    ended, why it failed, "" where it didn't, and what it cost, "" where unknown. A reply that isn't
    JSON is an earlier Release's, which ended well; one that is gone was deleted a week after."""
    base = os.path.join(folder, id)
    try:
        if _alive(int(_read(base + ".pid").strip())):
            return False, "", ""
    except ValueError:
        pass
    if not os.path.exists(base + ".txt"):
        return True, "", ""
    reply = _read(base + ".txt")
    if not reply.strip():
        first = _read(base + ".err").strip().split("\n")[0]
        return True, _flat(first) or "it ended with no reply", ""
    try:
        r = json.loads(reply)
    except ValueError:
        return True, "", ""
    if not isinstance(r, dict):
        return True, "", ""
    cost = r.get("total_cost_usd")
    cost = f"{cost:.2f}" if isinstance(cost, (int, float)) else ""
    errors = r.get("errors")
    if not r.get("is_error"):
        failed = ""
    elif r.get("subtype") == "error_max_budget_usd":
        failed = "it reached its budget of $" + _BUDGET
    elif isinstance(errors, list) and errors and isinstance(errors[0], str):
        failed = errors[0]
    else:
        failed = str(r.get("result") or r.get("subtype") or "it failed")
    return True, _flat(failed), cost


def _ended(root: str, data: str) -> List[str]:
    """Logs the end of each review of the repo at `root` that ended since, and returns what to tell
    the user of them: a review that failed, and one that read only the end of a conversation. Each
    is told once, to the first session that looks."""
    name, folder = repo(root), _folder(root, data)
    started: Dict[str, str] = {}
    for field in _runs(data, name):
        if field[3] == "started":
            started[field[2]] = field[5]
        else:
            started.pop(field[2], None)
    lines: List[str] = []
    for id, detail in started.items():
        done, failed, cost = _outcome(folder, id)
        if not done:
            continue
        try:
            _log_run(data, name, id, "failed" if failed else "ok", cost, failed)
        except OSError:
            continue
        m = re.fullmatch(r"read (\d+) of (\d+) characters", detail)
        read, of = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        if failed:
            lines.append(
                f"the Session review {id} failed, so nothing of its session is proposed: {failed}: "
                "tell the user"
            )
        elif read < of:
            lines.append(
                f"the Session review {id} read only the last {read} of the {of} characters of its "
                "session's conversation, so nothing settled before them is proposed: tell the user"
            )
    return lines


def week(root: str, data: str) -> Tuple[int, float]:
    """How many reviews of the repo at `root` failed in the last week, and what those that ended
    cost, in US dollars, as far as their replies said."""
    since = datetime.now(timezone.utc).timestamp() - _KEPT
    failed, cost = 0, 0.0
    for field in _runs(data, repo(root)):
        try:
            at = datetime.strptime(field[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if at.timestamp() < since or field[3] == "started":
            continue
        if field[3] == "failed":
            failed += 1
        try:
            cost += float(field[4])
        except ValueError:
            pass
    return failed, cost


def _from(folder: str, session: str, size: int) -> int:
    """Where in the Transcript of the session `session`, `size` long, its review starts reading,
    its reviews' files in `folder`: where the last review of it stopped, as a resumed session keeps
    its Transcript; where that one started, if it failed; the start, for a session not reviewed yet
    or a Transcript shorter than what was read."""
    field = _read(os.path.join(folder, "sessions", os.path.basename(session))).split()
    try:
        to, at, id = int(field[0]), int(field[1]), field[2]
    except (IndexError, ValueError):
        return 0
    if to > size:
        return 0
    done, failed, _ = _outcome(folder, id)
    return at if done and failed else to


def _mark(folder: str, session: str, id: str, at: int, to: int) -> None:
    """Records that the review `id` of the session `session` read its Transcript from `at` to
    `to`."""
    sessions = os.path.join(folder, "sessions")
    try:
        os.makedirs(sessions, mode=0o700, exist_ok=True)
        _write(os.path.join(sessions, os.path.basename(session)), f"{to} {at} {id}\n")
    except OSError:
        pass


def _rejected(root: str, data: str, most: int) -> List[str]:
    """The Proposals of the repo at `root` the user rejected, as "<target>: <title>", the last
    `most` of them, oldest first."""
    logged = _decisions(data, repo(root))
    files = []
    for folder in (os.path.join(_folder(root, data), "decided"), os.path.join(root, names.PROPOSALS)):
        files += [os.path.join(folder, n) for n in _names(folder) if n.endswith(".md")]
    files.sort(key=os.path.basename)
    out = []
    for file in files:
        review = os.path.basename(file)[: -len(".md")]
        for p in parse(review, _read(file)):
            if logged.get(p.review + "/" + p.id, ("", 0))[0] == REJECTED:
                out.append(p.target + ": " + p.title)
    return out[-most:] if most else []
