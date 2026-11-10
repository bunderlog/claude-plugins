"""The plugin's Status line (ADR status-line): the line drawn from what Claude Code gives a status
line command, and the command set in a project's settings."""

from __future__ import annotations

import math
import re
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from bagheera import names

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

# Each part's icon, in place of its label.
_ICONS = {"context": "▤", "5h": "◷", "7d": "◷", "cache": "↻"}
# The icons of how many sessions wait and how many projects need attention (PRD visibility).
WAITING, ATTENTION = "⧗", "⚑"

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

    def render(self, in_: Input, branch: str, columns: int, waiting: int = 0,
               attention: int = 0) -> str:
        """The Status line for a terminal `columns` wide, grey but for what is past a threshold:
        the project's folder and the branch on the left, the parts centered, and on the right
        how many sessions wait and how many projects need attention, in yellow where not 0, and the
        model with its effort flush with the right edge, the groups a dot apart. When the
        line is too narrow it drops the details, then the model."""
        width = max(40, columns - _MARGIN)
        folder = os.path.basename((in_.project_dir or in_.current_dir).rstrip("/"))
        left = _grey(" ".join(p for p in (folder, branch) if p)) if folder or branch else ""
        marks = [_paint(_YELLOW, icon + " " + str(n))
                 for icon, n in ((WAITING, waiting), (ATTENTION, attention)) if n > 0]
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


def branch(folder: str) -> str:
    """The branch checked out in `folder`, or its commit when detached; "" outside a repo."""
    if not folder:
        return ""

    def git(*args: str) -> Tuple[str, bool]:
        try:
            p = subprocess.run(
                ["git", "--no-optional-locks", "-C", folder, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except OSError:
            return "", False
        return p.stdout.strip(), p.returncode == 0

    name, ok = git("branch", "--show-current")
    if not ok or name:
        return name
    return git("rev-parse", "--short", "HEAD")[0]


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
