"""The plugin's Status line (ADR status-line): the line drawn from what Claude Code gives a status
line command, and the command set in a project's settings."""

from __future__ import annotations

import math
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from baloo import binlink, names, settings

# The Status line's bars, by their names in the Config, in the order it shows them without one.
BARS = ["context", "5h", "7d", "cache"]


@dataclass
class Thresholds:
    """The percentages at which a bar turns yellow and red: for a Usage bar, of what is used, from
    them up; for the Cache bar, of the cache's lifetime left, below them."""

    yellow: int
    red: int


def ordered(name: str, t: Thresholds) -> bool:
    """Whether `t` turns the bar `name` yellow before red."""
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
    model: str = ""
    effort: str = ""
    # None before Claude Code has one.
    context_window: Optional[ContextWindow] = None
    # None before the main conversation's first reply.
    prompt_cache: Optional[PromptCache] = None
    five_hour: Limit = field(default_factory=Limit)
    seven_day: Limit = field(default_factory=Limit)

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
        return cls(
            _str(_obj(v.get("workspace")).get("current_dir")),
            _str(_obj(v.get("model")).get("display_name")),
            _str(_obj(v.get("effort")).get("level")),
            context,
            cache,
            Limit.parse(limits.get("five_hour")),
            Limit.parse(limits.get("seven_day")),
        )


# The seconds a cached prefix stays warm, by its TTL.
_LIFETIMES = {"5m": 300.0, "1h": 3600.0}

# The clock the Cache bar counts down by, in seconds; a test stops it.
now = time.time

_RESET = "\x1b[00m"


def _paint(code: str, text: str) -> str:
    return "\x1b[" + code + "m" + text + _RESET


def _label(text: str) -> str:
    return _paint("2;37", text)


def _round(x: float) -> int:
    """`x` rounded half away from zero, as Go's math.Round."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


def _blocks(pct: int, width: int) -> str:
    """A bar `width` wide, `pct` percent of it filled."""
    filled = pct * width // 100
    return "█" * filled + "░" * (width - filled)


def _bar(percent: float, width: int, t: Thresholds) -> str:
    """A Usage bar `width` wide and its percentage: dim green, yellow and red from `t`."""
    pct = _round(min(100.0, max(0.0, percent)))
    color = "2;32"
    if pct >= t.red:
        color = "2;31"
    elif pct >= t.yellow:
        color = "2;33"
    return _paint(color, _blocks(pct, width)) + " " + str(pct) + "%"


def _thousands(tokens: float) -> str:
    """`tokens` in thousands, as "(120K)"."""
    return _paint("2;90", f"({_round(tokens / 1000)}K)")


def _cache(c: PromptCache, width: int, t: Thresholds, show_size: bool) -> str:
    """The Cache bar `width` wide: filled with the share of the cache's lifetime left, dim green,
    then yellow and red below `t`, and empty when cold; then the minutes until the cache goes cold,
    rounded up, or that it is cold, in dim red; then, with `show_size`, the cache's size, the
    tokens the next request writes again once it is cold."""
    left = 0.0
    if c.warm and c.expires_at is not None:
        left = c.expires_at - float(int(now()))
    pct, state = 0, _paint("2;31", "cold")
    if left > 0:
        # A TTL it doesn't know shows full.
        pct = _round(left / max(_LIFETIMES.get(c.ttl, 0.0), left) * 100)
        state = str(int(math.ceil(left / 60))) + "m"
    color = "2;32"
    if left <= 0 or pct < t.red:
        color = "2;31"
    elif pct < t.yellow:
        color = "2;33"
    part = _paint(color, _blocks(pct, width)) + " " + state
    tokens = c.recache_tokens_if_cold
    if show_size and tokens is not None and tokens > 0:
        part += " " + _thousands(tokens)
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


def _right(in_: Input) -> str:
    """The model and its effort when set, as "Opus 5.5 (high)"."""
    model = in_.model
    if not model:
        return ""
    if in_.effort:
        model += " (" + in_.effort + ")"
    return _label(model)


_COLOR_CODES = re.compile(r"\x1b\[[0-9;]*m")


def _visible(s: str) -> int:
    """How many columns `s` takes, its colors left out."""
    return len(_COLOR_CODES.sub("", s))


# The columns Claude Code keeps free beside the status line, two on each side; it cuts a longer one
# short.
_MARGIN = 4


@dataclass
class Layout:
    """The bars the Status line shows, in order, and each one's Thresholds."""

    bars: List[str]
    thresholds: Dict[str, Thresholds]

    def _middle(self, in_: Input, width: int, show_reset: bool) -> str:
        """The bars, in order, `width` wide, the 5-hour and 7-day ones with when they reset when
        `show_reset`."""
        parts = []
        for name in self.bars:
            t = self.thresholds.get(name, Thresholds(0, 0))
            if name == "context":
                c = in_.context_window
                if c is None:
                    continue
                # Before the first reply the context window has no percentage: it shows empty.
                used = c.used_percentage if c.used_percentage is not None else 0.0
                part = _label("Ctx") + " " + _bar(used, width, t)
                # The tokens the percentage counts, in thousands; none before the first reply.
                if c.total_input_tokens > 0:
                    part += " " + _thousands(c.total_input_tokens)
                parts.append(part)
            elif name == "cache":
                pc = in_.prompt_cache
                if pc is not None and pc.caching_observed:
                    # The cache's size is the context's tokens again: it shows only without them.
                    show_size = "context" not in self.bars
                    parts.append(_label("Cache") + " " + _cache(pc, width, t, show_size))
            elif name in ("5h", "7d"):
                limit = in_.five_hour if name == "5h" else in_.seven_day
                if limit.used_percentage is None:
                    continue
                part = _label(name) + " " + _bar(limit.used_percentage, width, t)
                if show_reset and limit.resets_at is not None:
                    when = _reset_time if name == "5h" else _reset_day
                    part += " " + _paint("2;90", "(" + when(limit.resets_at) + ")")
                parts.append(part)
        return " ".join(parts)

    def render(self, in_: Input, branch: str, columns: int) -> str:
        """The Status line for a terminal `columns` wide: the branch on the left, the bars
        centered, and the model with its effort flush with the right edge. When the line is too
        narrow it shrinks the bars, then drops the reset times, then the model."""
        width = max(40, columns - _MARGIN)
        left = _paint("01;35", branch) if branch else ""
        r = _right(in_)

        def fits(mid: str) -> bool:
            n = _visible(left) + _visible(mid) + 1
            if r:
                n += _visible(r) + 1
            return n <= width

        mid = ""
        for bar_width, show_reset in ((10, True), (5, True), (5, False)):
            mid = self._middle(in_, bar_width, show_reset)
            if fits(mid):
                break
        if not fits(mid):
            r = ""
        end = width - _visible(r) - 1 if r else width
        start = max(min((width - _visible(mid)) // 2, end - _visible(mid)), _visible(left) + 1)
        line = left + " " * (start - _visible(left)) + mid
        if not r:
            return line
        return line + " " * max(1, width - _visible(r) - _visible(line)) + r


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


def _command(link: str) -> str:
    """The status line command that runs the plugin through the link `link` (see binlink), marked
    as the plugin's."""
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
        # The seconds between runs while Claude Code is idle, so the Cache bar's minutes count
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


def _ours(raw: Any) -> bool:
    """Whether the statusLine setting `raw` is one the plugin wrote."""
    line = _line(raw)
    return line is not None and line[1].endswith(" " + names.MARKER)


def set_line(project: str, root: str, data: str, on: bool) -> Tuple[bool, Optional[Exception]]:
    """Sets the status line of the project at `project`, in the repo at `root`, or takes it out,
    as `on`, the Config's key, says. On, it sets the plugin's in the project's settings.local.json,
    where the plugin is enabled in its local, project or user settings and none of its local,
    project or managed settings has a status line the plugin didn't write; the user's own gives
    way. Off, or where one of those has a status line of its own, it takes the plugin's out. It
    returns whether it set one where the plugin's wasn't, and what went wrong, or None: a line can
    be set and still fail to go into info/exclude.

    The command runs the plugin through the link in `data`, the plugin's data folder (see
    binlink)."""
    files = settings.files(project)
    try:
        fields = settings.read_all(files)
    except (OSError, ValueError) as e:
        return False, e
    local = files[settings.LOCAL]
    had = "statusLine" in fields[settings.LOCAL]
    current = fields[settings.LOCAL].get("statusLine")
    mine = had and _ours(current)
    theirs = had and not mine
    for scope in (settings.PROJECT, settings.MANAGED):
        if "statusLine" in fields[scope]:
            theirs = True
    try:
        if not on or theirs:
            if mine:
                settings.delete(local, "statusLine")
            return False, None
        if not mine and not settings.enabling(fields):
            return False, None
        link = binlink.point(data)
        want = ("command", _command(link), 0, 60)
        if mine and _line(current) == want:
            return False, None
        value = {"type": want[0], "command": want[1], "padding": want[2], "refreshInterval": want[3]}
        created = settings.set_field(local, "statusLine", value)
    except (OSError, ValueError) as e:
        return False, e
    if created:
        try:
            settings.exclude(root, local)
        except (OSError, ValueError) as e:
            return not mine, e
    return not mine, None
