"""The plugin's Status line (ADR status-line): the line drawn from what Claude Code gives a status
line command, and the command set in a project's settings."""

from __future__ import annotations

import json
import math
import re
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bagheera import names, version

# The Status line's parts, each once a bar, in the order it shows them.
BARS = ["context", "5h", "7d", "cache"]


@dataclass
class Thresholds:
    """The percentages at which a part turns yellow and red: for a Usage part, of what is used,
    from them up; for the cache's, of its lifetime left, below them."""

    yellow: int
    red: int


def ordered(name: str, t: Thresholds) -> bool:
    """Whether `t` turns the part `name` yellow before red."""
    if name == "cache":
        return t.yellow >= t.red
    return t.yellow <= t.red


# The text of a JSON value Claude Code gives, as Go's decoder took it: a field of another type is
# left at its zero value.


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _str(v: Any) -> str:
    return v if isinstance(v, str) else ""


def _obj(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


@dataclass
class Limit:
    """One of the rate limits; a field Claude Code doesn't give is None."""

    used_percentage: Optional[float] = None
    resets_at: Optional[float] = None

    @classmethod
    def parse(cls, v: Any) -> Limit:
        o = _obj(v)
        return cls(_num(o.get("used_percentage")), _num(o.get("resets_at")))


@dataclass
class ContextWindow:
    """The context window; used_percentage is None before the first reply."""

    used_percentage: Optional[float] = None
    total_input_tokens: float = 0


@dataclass
class PromptCache:
    """The main conversation's prompt cache; a field Claude Code doesn't give is None."""

    warm: bool = False
    # False while no reply has used the cache: caching is off.
    caching_observed: bool = False
    ttl: str = ""
    expires_at: Optional[float] = None
    # The cache's size: what the next request writes to it again once it is cold; None right
    # after a compaction.
    recache_tokens_if_cold: Optional[float] = None


@dataclass
class Input:
    """What Claude Code gives a status line command on stdin, the part the Status line shows."""

    current_dir: str = ""
    # The folder Claude Code runs in, which a command's cd doesn't change.
    project_dir: str = ""
    model: str = ""
    effort: str = ""
    # None before Claude Code has one.
    context_window: Optional[ContextWindow] = None
    # None before the main conversation's first reply.
    prompt_cache: Optional[PromptCache] = None
    five_hour: Limit = field(default_factory=Limit)
    seven_day: Limit = field(default_factory=Limit)
    session_id: str = ""

    @classmethod
    def parse(cls, value: Any) -> Input:
        """The Input in the decoded JSON `value`; what isn't there, or isn't of its type, is left
        out."""
        v = _obj(value)
        context = None
        if isinstance(v.get("context_window"), dict):
            c = v["context_window"]
            context = ContextWindow(
                _num(c.get("used_percentage")), _num(c.get("total_input_tokens")) or 0
            )
        cache = None
        if isinstance(v.get("prompt_cache"), dict):
            c = v["prompt_cache"]
            cache = PromptCache(
                c.get("warm") is True,
                c.get("caching_observed") is True,
                _str(c.get("ttl")),
                _num(c.get("expires_at")),
                _num(c.get("recache_tokens_if_cold")),
            )
        limits = _obj(v.get("rate_limits"))
        workspace = _obj(v.get("workspace"))
        return cls(
            _str(workspace.get("current_dir")),
            _str(workspace.get("project_dir")),
            _str(_obj(v.get("model")).get("display_name")),
            _str(_obj(v.get("effort")).get("level")),
            context,
            cache,
            Limit.parse(limits.get("five_hour")),
            Limit.parse(limits.get("seven_day")),
            _str(v.get("session_id")),
        )


# The seconds a cached prefix stays warm, by its TTL.
_LIFETIMES = {"5m": 300.0, "1h": 3600.0}

# The clock the cache's minutes count down by, in seconds; a test stops it.
now = time.time

_RESET = "\x1b[00m"

# The colors of the line: grey while all is well, yellow and red past a threshold.
_GREY, _YELLOW, _RED = "90", "33", "31"
# The project's folder light cyan and the branch light blue, as Claude Code draws inline code, so
# the eye finds which project and branch a terminal shows.
_FOLDER, _BRANCH = "96", "38;2;177;185;249"

# Each part's icon, in place of its label.
_ICONS = {"context": "▤", "5h": "◷", "7d": "◷", "cache": "↻"}
# The icons of how many sessions wait and how many projects need attention (PRD visibility), and
# of a newer version installed, which a restart runs (PRD status-line).
WAITING, ATTENTION, RESTART = "⧗", "⚑", "⇡"


@dataclass
class Marks:
    """What the line shows beside Claude Code's input: in the clone, how many entries `git status`
    lists and how many commits aren't pushed (PRD status-line); on the machine, how many sessions
    wait and how many projects need attention (PRD visibility); and the version a restart runs."""

    changed: int = 0
    ahead: int = 0
    waiting: int = 0
    attention: int = 0
    restart: str = ""

# The least room between the line's left, middle and right; a group's own parts are one space
# apart.
_GAP = "   "


def _paint(code: str, text: str) -> str:
    return "\x1b[" + code + "m" + text + _RESET


def _grey(text: str) -> str:
    return _paint(_GREY, text)


# What sits between two groups of the middle or of the right, as Claude Code's own footer has it.
_DOT = " " + _grey("·") + " "


def _round(x: float) -> int:
    """`x` rounded half away from zero, as Go's math.Round."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def _used(name: str, percent: float, t: Thresholds) -> str:
    """The icon of the Usage part `name` and its percentage, grey, then yellow and red from `t`."""
    pct = _round(min(100.0, max(0.0, percent)))
    color = _GREY
    if pct >= t.red:
        color = _RED
    elif pct >= t.yellow:
        color = _YELLOW
    return _paint(color, _ICONS[name] + " " + str(pct) + "%")


def _thousands(tokens: float) -> str:
    """`tokens` in thousands, as "120K"."""
    return f"{_round(tokens / 1000)}K"


def _cache(c: PromptCache, t: Thresholds, show_size: bool, details: bool) -> str:
    """The cache's part: its icon and the minutes until the cache goes cold, rounded up, or that
    it is cold; grey, then yellow and red below `t` of its lifetime left, and red when cold; then,
    with `show_size` and `details`, the cache's size, the tokens the next request writes again once
    it is cold."""
    left = 0.0
    if c.warm and c.expires_at is not None:
        left = c.expires_at - float(int(now()))
    pct, state = 0, "cold"
    if left > 0:
        # A TTL it doesn't know counts as full.
        pct = _round(left / max(_LIFETIMES.get(c.ttl, 0.0), left) * 100)
        state = str(int(math.ceil(left / 60))) + "m"
    color = _GREY
    if left <= 0 or pct < t.red:
        color = _RED
    elif pct < t.yellow:
        color = _YELLOW
    part = _paint(color, _ICONS["cache"] + " " + state)
    tokens = c.recache_tokens_if_cold
    if show_size and details and tokens is not None and tokens > 0:
        part += " " + _grey(_thousands(tokens))
    return part


def _reset_time(epoch_seconds: float) -> str:
    """"HH:MM" in local time: the 5-hour window resets within 5 hours, so the day goes without
    saying."""
    return time.strftime("%H:%M", time.localtime(int(epoch_seconds)))


_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _reset_day(epoch_seconds: float) -> str:
    """The weekday, in local time, as "Mon", whatever the locale: the 7-day window resets within a
    week, so the day says when."""
    return _WEEKDAYS[time.localtime(int(epoch_seconds)).tm_wday]


def _model(in_: Input) -> str:
    """The model and its effort when set, as "Opus 5.5 high", grey."""
    model = in_.model
    if not model:
        return ""
    if in_.effort:
        model += " " + in_.effort
    return _grey(model)


_COLOR_CODES = re.compile(r"\x1b\[[0-9;]*m")


def _visible(s: str) -> int:
    """How many columns `s` takes, its colors left out."""
    return len(_COLOR_CODES.sub("", s))


# The columns Claude Code keeps free beside the status line, two on each side; it cuts a longer one
# short.
_MARGIN = 4


@dataclass
class Layout:
    """The parts the Status line shows, in order, and each one's Thresholds."""

    bars: List[str]
    thresholds: Dict[str, Thresholds]

    def _middle(self, in_: Input, details: bool) -> str:
        """The parts, in order, each its icon and number, with the details after it (the context's
        tokens, when each limit resets) when `details`."""
        parts = []
        for name in self.bars:
            t = self.thresholds.get(name, Thresholds(0, 0))
            if name == "context":
                c = in_.context_window
                if c is None:
                    continue
                # Before the first reply the context window has no percentage: it shows 0.
                used = c.used_percentage if c.used_percentage is not None else 0.0
                part = _used(name, used, t)
                # The tokens the percentage counts, in thousands; none before the first reply.
                if details and c.total_input_tokens > 0:
                    part += " " + _grey(_thousands(c.total_input_tokens))
                parts.append(part)
            elif name == "cache":
                pc = in_.prompt_cache
                if pc is not None and pc.caching_observed:
                    # The cache's size is the context's tokens again: it shows only without them.
                    show_size = "context" not in self.bars
                    parts.append(_cache(pc, t, show_size, details))
            elif name in ("5h", "7d"):
                limit = in_.five_hour if name == "5h" else in_.seven_day
                if limit.used_percentage is None:
                    continue
                part = _used(name, limit.used_percentage, t)
                if details and limit.resets_at is not None:
                    when = _reset_time if name == "5h" else _reset_day
                    part += " " + _grey(when(limit.resets_at))
                parts.append(part)
        return _DOT.join(parts)

    def render(self, in_: Input, branch: str, columns: int, m: Optional[Marks] = None) -> str:
        """The Status line for a terminal `columns` wide, grey but for what is past a threshold:
        the project's folder light cyan, the branch light blue and, grey, what isn't committed or
        pushed on the left, the parts
        centered, and on the right how many sessions wait, how many projects need attention and a
        restart, in yellow where there, and the model with its effort flush with the right edge,
        the groups a dot apart. When the line is too narrow it drops the details, then the model,
        then cuts the folder's name short, then drops the figures."""
        m = m or Marks()
        width = max(40, columns - _MARGIN)
        folder = os.path.basename((in_.project_dir or in_.current_dir).rstrip("/"))
        work = [_grey(s + str(n)) for s, n in (("±", m.changed), ("↑", m.ahead)) if n > 0]
        tail = " ".join(([_paint(_BRANCH, branch)] if branch else []) + work)
        marks = [_paint(_YELLOW, icon + " " + str(n))
                 for icon, n in ((WAITING, m.waiting), (ATTENTION, m.attention)) if n > 0]
        if m.restart:
            marks.append(_paint(_YELLOW, RESTART + " " + m.restart))

        def left_of(name: str) -> str:
            return " ".join(p for p in ((_paint(_FOLDER, name) if name else ""), tail) if p)

        left = left_of(folder)
        model = _model(in_)
        r = _DOT.join(marks + ([model] if model else []))

        def fits(mid: str) -> bool:
            n = _visible(left) + (len(_GAP) if left else 0) + _visible(mid)
            if r:
                n += len(_GAP) + _visible(r)
            return n <= width

        mid = self._middle(in_, True)
        if not fits(mid):
            mid = self._middle(in_, False)
        if not fits(mid):
            r = _DOT.join(marks)
        if not fits(mid) and len(folder) > 1:
            over = _visible(left) + len(_GAP) + _visible(mid) - width
            if r:
                over += len(_GAP) + _visible(r)
            keep = max(1, len(folder) - over - 1)
            left = left_of(folder[:keep] + "…")
        if not fits(mid):
            mid = ""
        gap = len(_GAP) if left else 0
        end = width - _visible(r) - len(_GAP) if r else width
        start = max(min((width - _visible(mid)) // 2, end - _visible(mid)), _visible(left) + gap)
        line = left + " " * (start - _visible(left)) + mid
        if not r:
            return line.rstrip(" ") if not mid else line
        return line + " " * max(len(_GAP), width - _visible(r) - _visible(line)) + r


def default() -> Layout:
    """The Layout where the Config sets none: every bar, at the thresholds of ADR status-line; a
    new one each time, so a change to one is no other's."""
    return Layout(
        list(BARS),
        {
            "context": Thresholds(15, 20),
            "cache": Thresholds(40, 20),
            "5h": Thresholds(70, 85),
            "7d": Thresholds(80, 95),
        },
    )


# The folder of the plugin's data folder that holds, by session, the version its session start
# ran: the line runs through a link a later session's start points at a newer copy, so it can't
# tell the session's version from its own (PRD status-line).
SESSIONS = "sessions"
# How long a session's version is kept: a week.
KEPT = 7 * 24 * 3600


def record(data: str, session: str, ran: str) -> None:
    """Keeps, in the plugin's data folder `data`, that the session `session` runs the version
    `ran`, and forgets those kept over KEPT."""
    if not data or not session or os.sep in session:
        return
    folder = os.path.join(data, SESSIONS)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    now = time.time()
    for e in os.scandir(folder):
        if now - e.stat().st_mtime > KEPT:
            os.remove(e.path)
    with open(os.path.join(folder, session), "w", encoding="utf-8") as f:
        f.write(ran)


def _numbers(v: str) -> Optional[Tuple[int, ...]]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return None


def restart(data: str, session: str, root: str) -> str:
    """The version installed for the repo at `root`, as "0.54", where it is newer than the one the
    session `session` started on, which only a restart runs; "" otherwise."""
    try:
        with open(os.path.join(data, SESSIONS, session), encoding="utf-8") as f:
            ran = f.read().strip()
    except OSError:
        return ""
    there = version.installed(root)
    running, newer = _numbers(ran), _numbers(there)
    if not (running and newer and newer > running):
        return ""
    return ".".join(there.split(".")[:2])


# The file of the plugin's data folder that keeps the latest 5-hour and 7-day limits any session
# got (PRD status-line).
LIMITS = "limits.json"


def _latest(given: Limit, kept: Any) -> Limit:
    """Of the limit `given` and the one `kept` as [used_percentage, resets_at], the highest
    percentage whose reset is still ahead: use only grows until the limit resets. A given one
    without its reset counts as ahead."""
    t = now()
    got = Limit()
    if given.used_percentage is not None and (given.resets_at is None or given.resets_at > t):
        got = given
    if isinstance(kept, list) and len(kept) == 2:
        k = Limit(_num(kept[0]), _num(kept[1]))
        if (k.used_percentage is not None and k.resets_at is not None and k.resets_at > t
                and (got.used_percentage is None or k.used_percentage > got.used_percentage)):
            got = k
    return got


def limits(in_: Input, data: str) -> None:
    """Sets `in_`'s 5-hour and 7-day limits to the latest any session got, kept in the plugin's
    data folder `data`, and keeps them there where they are newer: Claude Code gives each session
    only what its own last reply said (PRD status-line)."""
    path = os.path.join(data, LIMITS)
    try:
        with open(path, encoding="utf-8") as f:
            kept = _obj(json.load(f))
    except (OSError, ValueError):
        kept = {}
    in_.five_hour = _latest(in_.five_hour, kept.get("five_hour"))
    in_.seven_day = _latest(in_.seven_day, kept.get("seven_day"))
    keep = {
        name: [limit.used_percentage, limit.resets_at]
        for name, limit in (("five_hour", in_.five_hour), ("seven_day", in_.seven_day))
        if limit.used_percentage is not None and limit.resets_at is not None
    }
    if keep and keep != kept:
        try:
            tmp = f"{path}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(keep, f)
            os.replace(tmp, path)
        except OSError:
            pass


# How long the line waits for git, in seconds, before it shows what it last got.
WAIT = 0.15
# The file of the plugin's data folder that keeps what the line last got from git, by folder.
COUNTS = "counts.json"


@dataclass
class Work:
    """What git says of the clone a folder is in: the branch checked out, or its commit when
    detached, "" outside a repo; how many entries `git status` lists; and how many commits on what
    is checked out aren't on its upstream, or, without one, on `origin/HEAD` (PRD status-line)."""

    branch: str = ""
    changed: int = 0
    ahead: int = 0


def work(folder: str, data: str) -> Work:
    """What git says of the clone `folder` is in. It runs nothing that fetches, runs git's
    commands side by side and waits for them at most WAIT, and past that gives what it last got in
    `folder`, kept in the plugin's data folder `data`, or nothing."""
    if not folder:
        return Work()
    base = ["git", "--no-optional-locks", "-C", folder]
    commands = [
        base + ["branch", "--show-current"],
        base + ["rev-parse", "--short", "HEAD"],
        base + ["status", "--porcelain"],
        base + ["rev-list", "--count", "@{upstream}..HEAD"],
        base + ["rev-list", "--count", "origin/HEAD..HEAD"],
    ]
    try:
        procs = [subprocess.Popen(c, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                 for c in commands]
    except OSError:
        return Work()
    deadline = time.monotonic() + WAIT
    outs: List[Optional[Tuple[str, bool]]] = []
    for p in procs:
        try:
            out, _ = p.communicate(timeout=max(0.0, deadline - time.monotonic()))
            outs.append((out.strip(), p.returncode == 0))
        except subprocess.TimeoutExpired:
            # Not communicate: a child git left holds the pipe open until it ends.
            p.kill()
            p.wait()
            if p.stdout:
                p.stdout.close()
            outs.append(None)
    path = os.path.join(data, COUNTS) if data else ""
    kept: Dict[str, Any] = {}
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                kept = _obj(json.load(f))
        except (OSError, ValueError):
            kept = {}
    if any(o is None for o in outs):
        last = kept.get(folder)
        if (isinstance(last, list) and len(last) == 3 and isinstance(last[0], str)
                and all(isinstance(n, int) for n in last[1:])):
            return Work(last[0], last[1], last[2])
        return Work()
    (name, named), (commit, _), (status, ok), *ahead = outs  # type: ignore[misc]
    if not named or not ok:
        return Work()
    got = Work(name or commit, len([line for line in status.splitlines() if line.strip()]))
    for out, done in ahead:  # type: ignore[misc]
        if done and out.isdigit():
            got.ahead = int(out)
            break
    if path and kept.get(folder) != [got.branch, got.changed, got.ahead]:
        kept[folder] = [got.branch, got.changed, got.ahead]
        try:
            tmp = f"{path}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(kept, f)
            os.replace(tmp, path)
        except OSError:
            pass
    return got


def _quote(s: str) -> str:
    """`s` quoted for sh."""
    return "'" + s.replace("'", "'\\''") + "'"


def command(link: str) -> str:
    """The status line command that runs the plugin through the link `link` (see binlink), marked
    as the plugin's, for the person to set in their own settings (PRD no-config)."""
    run = link + "/scripts/run.py"
    return "python3 -E -s " + _quote(run) + " status-line " + names.MARKER


def _line(raw: Any) -> Optional[Tuple[str, str, int, int]]:
    """Claude Code's statusLine setting `raw` as its type, command, padding and refreshInterval,
    each left out at its zero value; None where it isn't an object of fields of those types."""
    if not isinstance(raw, dict):
        return None
    got: List[Any] = []
    for key, kind, zero in (
        ("type", str, ""),
        ("command", str, ""),
        ("padding", int, 0),
        # The seconds between runs while Claude Code is idle, so the Cache figure's minutes count
        # down.
        ("refreshInterval", int, 0),
    ):
        v = raw.get(key, zero)
        if v is None:
            v = zero
        if not isinstance(v, kind) or isinstance(v, bool):
            return None
        got.append(v)
    return got[0], got[1], got[2], got[3]


def ours(raw: Any) -> bool:
    """Whether the statusLine setting `raw` is one the plugin's command marks, or an earlier baloo
    wrote into a clone's settings.local.json."""
    line = _line(raw)
    return line is not None and (
        line[1].endswith(" " + names.MARKER) or line[1].endswith(" " + names.OLD_MARKER)
    )
