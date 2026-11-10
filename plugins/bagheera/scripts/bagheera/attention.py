"""Which of the machine's projects need attention, and which sessions wait for their person (PRD
visibility): the Hooks mark a session waiting and clear it, a check finds the projects and what
each needs and keeps it in the plugin's data folder, and the Status line and doctor read it."""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from bagheera import names, repo, review, setup

# How recent a Transcript's change makes its folder one of the machine's projects.
DAYS = 30
# The folder of the plugin's data folder that holds a file per session waiting.
WAITING = "waiting"
# The file of the plugin's data folder that holds what the last check found.
FOUND = "attention.json"
# The file that marks a check running, since when, so the line starts no second one.
RUNNING = "attention.running"
# How old, in seconds, what the check found may get before the line starts another: what the line
# shows is then at most this and the check's own time old.
FRESH = 30
# How long a check may take before another may start, in case one died midway.
STALE = 120
# How long a mark is kept without its session's Claude Code known to have exited: a week.
KEPT = 7 * 24 * 3600
# How much of a Transcript's end is read for an entry after a mark.
TAIL = 256 * 1024


@dataclass
class Need:
    """One thing a project needs, and what to do about it."""

    what: str
    fix: str


@dataclass
class Project:
    """One of the machine's projects: its main working tree, whether it is set up at all, and what
    it needs."""

    root: str
    set_up: bool
    needs: List[Need] = field(default_factory=list)


@dataclass
class Wait:
    """A session waiting for its person: its id, its project's folder and since when."""

    session: str
    root: str
    since: float


@dataclass
class Found:
    """What a check found, and when."""

    at: float = 0.0
    projects: List[Project] = field(default_factory=list)
    waits: List[Wait] = field(default_factory=list)

    def waiting(self, session: str) -> int:
        """How many sessions wait, but `session`, the one asking."""
        return len([w for w in self.waits if w.session != session])

    def attention(self) -> int:
        """How many projects need attention."""
        return len([p for p in self.projects if p.needs])


# Marks


def mark(data: str, session: str, cwd: str, transcript: str, pid: int, now: float) -> None:
    """Marks the session `session`, in `cwd`, waiting for its person from `now`; `pid` is its
    Claude Code's, 0 where unknown, and `transcript` its Transcript."""
    if not data or not session or os.sep in session:
        return
    folder = os.path.join(data, WAITING)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    tmp = os.path.join(folder, f".{session}.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"cwd": cwd, "transcript": transcript, "pid": pid, "since": now}, f)
    os.replace(tmp, os.path.join(folder, session))


def clear(data: str, session: str) -> None:
    """Clears the session `session`'s mark: it no longer waits."""
    if not data or not session or os.sep in session:
        return
    try:
        os.remove(os.path.join(data, WAITING, session))
    except OSError:
        pass


def claude_pid() -> int:
    """The process id of the Claude Code that runs this Hook, which runs `sh`, which runs this; 0
    where it can't be told."""
    try:
        p = subprocess.run(["ps", "-o", "ppid=", "-p", str(os.getppid())], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, timeout=2)
        return int(p.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def _alive(pid: int) -> bool:
    if pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _answered(transcript: str, since: float) -> bool:
    """Whether the Transcript at `transcript` holds an entry of the person or of Claude after
    `since`: a question or a permission answered, a prompt sent. Claude Code's own entries after a
    turn's end, such as its Hooks' summary, don't count."""
    try:
        with open(transcript, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TAIL))
            lines = f.read().splitlines()
    except OSError:
        return False
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("type") not in ("user", "assistant"):
            continue
        at = _time(entry.get("timestamp"))
        if at is None:
            continue
        return at > since
    return False


def _time(stamp: Any) -> Optional[float]:
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def waits(data: str, now: float) -> List[Wait]:
    """The sessions waiting, longest first; a mark whose session's Claude Code exited, whose
    Transcript went on, or older than KEPT is cleared."""
    folder = os.path.join(data, WAITING)
    out: List[Wait] = []
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    for e in entries:
        if e.name.startswith("."):
            continue
        try:
            with open(e.path, encoding="utf-8") as f:
                m = json.load(f)
            since = float(m["since"])
            pid = int(m.get("pid") or 0)
        except (OSError, ValueError, KeyError, TypeError):
            clear(data, e.name)
            continue
        transcript = m.get("transcript") if isinstance(m.get("transcript"), str) else ""
        if now - since > KEPT or not _alive(pid) or (transcript and _answered(transcript, since)):
            clear(data, e.name)
            continue
        cwd = m.get("cwd") if isinstance(m.get("cwd"), str) else ""
        out.append(Wait(e.name, main_tree(repo.root(cwd)) if cwd else "", since))
    return sorted(out, key=lambda w: w.since)


# Projects


def main_tree(root: str) -> str:
    """The main working tree of the repo at `root`, which a linked worktree counts as; `root`
    where git can't tell, "" for none."""
    if not root:
        return ""
    try:
        p = subprocess.run(["git", "--no-optional-locks", "-C", root, "rev-parse",
                            "--git-common-dir"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return root
    common = p.stdout.strip()
    if p.returncode != 0 or not common:
        return root
    common = os.path.normpath(os.path.join(root, common))
    return os.path.dirname(common) if os.path.basename(common) == ".git" else root


def _cwd(transcript: str) -> str:
    """The folder the first of the Transcript's entries that names one names."""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for _, line in zip(range(64), f):
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and isinstance(entry.get("cwd"), str):
                    return entry["cwd"]
    except OSError:
        pass
    return ""


def projects(config: str, now: float) -> List[str]:
    """The machine's projects: the main working tree of each repo a Transcript in Claude Code's
    folder `config`, modified in the last DAYS, was in, sorted."""
    folder = os.path.join(config, "projects")
    files = glob.glob(os.path.join(glob.escape(folder), "*", "*.jsonl"))
    files += glob.glob(os.path.join(glob.escape(folder), "*", "*", "subagents", "*.jsonl"))
    cwds = set()
    for file in files:
        try:
            if now - os.path.getmtime(file) > DAYS * 24 * 3600:
                continue
        except OSError:
            continue
        cwd = _cwd(file)
        if cwd and os.path.isdir(cwd):
            cwds.add(cwd)
    roots = {main_tree(repo.root(cwd)) for cwd in cwds}
    return sorted(r for r in roots if r)


_KEPT_LINE = re.compile(r" · kept [0-9]{4}-[0-9]{2}-[0-9]{2}\s*$")


def inbox_left(text: str) -> int:
    """How many items of the Inbox `text` aren't gone through yet: a `## ` heading outside a
    fenced block whose first non-blank line after it doesn't end ` · kept <date>`, as baloo's
    session start counts them."""
    left, fenced, heading = 0, False, False
    for line in text.splitlines():
        if line.startswith("```") or line.startswith("~~~"):
            fenced = not fenced
        if fenced:
            continue
        if line.startswith("## "):
            if heading:
                left += 1
            heading = True
            continue
        if heading and line.strip():
            if not _KEPT_LINE.search(line):
                left += 1
            heading = False
    return left + (1 if heading else 0)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def needs(root: str, data: str) -> List[Need]:
    """What the project at `root` needs, each with what to do about it."""
    out: List[Need] = []
    n = len([it for it in review.items(root, data) if it.pending or it.mismatch])
    if n:
        out.append(Need(f"{n} Proposal{'s' if n > 1 else ''} wait",
                        "open a session there, which asks about each"))
    if setup.started(root):
        for item in setup.missing(root):
            out.append(Need(f"{item} is missing", f"{names.SETUP_SKILL} there"))
    command = setup.hooks_off(root)
    if command:
        out.append(Need("its Git hooks are off in this clone", command))
    n = inbox_left(_read(os.path.join(root, names.INBOX)))
    if n:
        out.append(Need(f"{n} Inbox item{'s' if n > 1 else ''} not gone through",
                        "/" + names.KNOWLEDGE + ":inbox there"))
    return out


# The check


def check(data: str, config: str, now: float) -> Found:
    """Finds the machine's projects, what each needs and the sessions waiting, and keeps it in the
    plugin's data folder `data` for the Status line."""
    found = Found(now)
    for root in projects(config, now):
        found.projects.append(Project(root, setup.started(root), needs(root, data)))
    found.waits = waits(data, now)
    if data:
        os.makedirs(data, mode=0o700, exist_ok=True)
        tmp = os.path.join(data, f".{FOUND}.{os.getpid()}")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(found), f)
        os.replace(tmp, os.path.join(data, FOUND))
    return found


def read(data: str) -> Found:
    """What the last check found, empty where none was kept or it can't be read."""
    try:
        with open(os.path.join(data, FOUND), encoding="utf-8") as f:
            raw = json.load(f)
        return Found(
            float(raw["at"]),
            [Project(p["root"], bool(p["set_up"]), [Need(**n) for n in p["needs"]])
             for p in raw["projects"]],
            [Wait(**w) for w in raw["waits"]],
        )
    except (OSError, ValueError, KeyError, TypeError):
        return Found()


def start(data: str, script: str, now: float) -> bool:
    """Starts a check in the background, running `script`, where what the last one found is older
    than FRESH and none runs; returns at once, whether it started one."""
    if not data or now - read(data).at < FRESH:
        return False
    running = os.path.join(data, RUNNING)
    try:
        with open(running, encoding="utf-8") as f:
            if now - float(f.read()) < STALE:
                return False
    except (OSError, ValueError):
        pass
    try:
        with open(running, "w", encoding="utf-8") as f:
            f.write(str(now))
        env = dict(os.environ, CLAUDE_PLUGIN_DATA=data)
        subprocess.Popen([sys.executable, "-E", "-s", script, "attention"], env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return False
    return True


def run_check(data: str, config: str) -> None:
    """The background check `start` runs; it clears the mark of a check running when done."""
    try:
        check(data, config, time.time())
    finally:
        try:
            os.remove(os.path.join(data, RUNNING))
        except OSError:
            pass
