"""Condenses Claude Code's Transcripts into what a Retro needs, masking anything that may be a
Secret (ADR transcripts)."""

# cspell:ignore ermission

from __future__ import annotations

import calendar
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from baloo import checks, names


@dataclass
class Event:
    """A moment of a session a Retro looks at, by the Transcript's line `at`, from 1."""

    at: int
    # prompt, command, interrupt or error.
    type: str
    # An error's: check, rejected, hook, classifier, permission, stale, exit or other.
    kind: str = ""
    # The failed tool call, by what it acts on: `Bash(go test ./...)`.
    call: str = ""
    text: str = ""

    def __str__(self) -> str:
        head = f"[{self.at}] {self.type}"
        if self.type == "interrupt":
            return head
        if self.type == "error":
            return f"{head} {self.kind} {_clip(self.call, _CALL_CHARS)}: {_gist(self, _ERROR_CHARS)}"
        return head + ": " + _clip(self.text, _PROMPT_CHARS)


@dataclass
class Repeat:
    """A tool call made `n` times."""

    call: str
    n: int


@dataclass
class Cost:
    """A tool call, by its result's line `at`, that added `tokens` tokens to the context."""

    at: int
    call: str
    tokens: int


@dataclass
class Session:
    """What a Retro needs of one session's Transcript."""

    id: str = ""
    title: str = ""
    # When the session started, `YYYY-MM-DD hh:mm` UTC; minutes, how long it ran.
    start: str = ""
    minutes: int = 0
    headless: bool = False
    # How many calls of each tool the session made.
    tools: Dict[str, int] = field(default_factory=dict)
    events: List[Event] = field(default_factory=list)
    # The calls made at least three times, commonest first.
    repeats: List[Repeat] = field(default_factory=list)
    # The calls that added the most to the context, costliest first.
    costs: List[Cost] = field(default_factory=list)
    # How many tokens each tool's calls added to the context.
    tokens: Dict[str, int] = field(default_factory=dict)

    def _charge(self, rs: List[_Result], other: int, tokens: int) -> None:
        """Spreads `tokens`, what the context grew by after the results `rs` and `other`
        characters of what else came (a prompt, Claude Code's attachments), over them by length:
        calls made in parallel come back to one response, and a call is charged only its own
        result's part."""
        if not rs or tokens <= 0:
            return
        chars = other + sum(r.chars for r in rs)
        for r in rs:
            n = tokens * r.chars // chars if chars > 0 else tokens // len(rs)
            if n <= 0:
                continue
            self.tokens[r.tool] = self.tokens.get(r.tool, 0) + n
            if n >= _COST_MIN:
                self.costs.append(Cost(r.at, r.call, n))

    def report(self) -> str:
        """The session for a Retro, masked."""
        calls = sum(self.tools.values())
        failed = sum(1 for e in self.events if e.type == "error")
        tools = sorted(self.tools, key=lambda name: (-self.tools[name], name))
        used = [f"{name} {self.tools[name]}" for name in tools] or ["none"]
        head = "# Session " + self.id
        if self.title:
            head += ": " + self.title
        out = [
            head,
            f"{self.start}, {self.minutes} min, {calls} tool calls, {failed} failed",
            "Tools: " + ", ".join(used),
            "",
        ]
        out.extend(str(e) for e in self.events)
        if self.repeats:
            out += ["", "Repeated calls:"]
            out.extend(f"{r.n}× {_clip(r.call, _CALL_CHARS)}" for r in self.repeats)
        if self.costs:
            out += ["", "Expensive calls, by the tokens they added to the context:"]
            out.extend(
                f"[{c.at}] {_kilo(c.tokens)} {_clip(c.call, _CALL_CHARS)}" for c in self.costs
            )
        return mask("\n".join(out))

    def worth(self) -> bool:
        """Whether the session is worth a Retro: not headless, and something besides /clear was
        typed or failed."""
        return not self.headless and any(
            e.type != "command" or not _CLEAR.match(e.text) for e in self.events
        )


_PROMPT_CHARS = 300
_ERROR_CHARS = 200
_CALL_CHARS = 120
_REPEAT_MIN = 3
_COST_MIN = 5000  # a call adding fewer tokens isn't worth a Retro's look
_TOP_COSTS = 5

# The tools whose repeated calls show Claude hunting for the same thing.
_REPEATED = ["Bash", "Read", "Grep", "Glob", "WebFetch"]

# The characters Go's strings.Fields and strings.TrimSpace take for space: Unicode's White_Space.
_SPACE = (
    "\t\n\v\f\r \x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009"
    "\u200a\u2028\u2029\u202f\u205f\u3000"
)
_SPACES = re.compile("[" + _SPACE + "]+")


def _fields(text: str) -> List[str]:
    return [f for f in _SPACES.split(text) if f]


def _trim(text: str) -> str:
    return text.strip(_SPACE)


@dataclass
class _Result:
    """A tool call's result, at the Transcript's line `at`, waiting for the next response's usage
    to tell what it cost."""

    at: int
    call: str
    tool: str
    chars: int


@dataclass
class _Block:
    type: str = ""
    text: str = ""
    id: str = ""
    name: str = ""
    input: Dict[str, Any] = field(default_factory=dict)
    tool_use_id: str = ""
    is_error: bool = False
    content: Any = None


# A line's fields of a known type: a line where one has another type is not read, as Go's decoder
# didn't read it.
_LINE_FIELDS = {
    "type": str,
    "isMeta": bool,
    "entrypoint": str,
    "timestamp": str,
    "cwd": str,
    "aiTitle": str,
}


def _reject(constant: str) -> Any:
    raise ValueError("not JSON: " + constant)


def _lines(transcript: Union[str, bytes]) -> Iterator[Tuple[int, Dict[str, Any]]]:
    """Each JSON line of the Transcript `transcript`, numbered from 1; a line that isn't a JSON
    object is skipped and not counted."""
    if isinstance(transcript, bytes):
        transcript = transcript.decode("utf-8", errors="replace")
    at = 0
    for raw in transcript.split("\n"):
        try:
            line = json.loads(raw, parse_constant=_reject)
        except ValueError:
            continue
        if line is None:
            line = {}
        if not isinstance(line, dict) or any(
            line.get(k) is not None and not _typed(line[k], t) for k, t in _LINE_FIELDS.items()
        ):
            continue
        at += 1
        yield at, line


def _typed(value: Any, kind: type) -> bool:
    return isinstance(value, kind) and (kind is bool or not isinstance(value, bool))


def _str(line: Dict[str, Any], key: str) -> str:
    return line.get(key) or ""


def _blocks(message: Any) -> List[_Block]:
    """The content blocks of a message `message`, a string's as one text block."""
    if not isinstance(message, dict):
        return []
    return _content(message.get("content"))


def _content(raw: Any) -> List[_Block]:
    """The blocks of `raw`, a string or a list of blocks."""
    if isinstance(raw, str):
        return [_Block(type="text", text=raw)]
    if not isinstance(raw, list):
        return []
    blocks = []
    for b in raw:
        if not isinstance(b, dict):
            continue
        blocks.append(
            _Block(
                type=_field(b, "type", str, ""),
                text=_field(b, "text", str, ""),
                id=_field(b, "id", str, ""),
                name=_field(b, "name", str, ""),
                input=_field(b, "input", dict, {}),
                tool_use_id=_field(b, "tool_use_id", str, ""),
                is_error=_field(b, "is_error", bool, False),
                content=b.get("content"),
            )
        )
    return blocks


def _field(b: Dict[str, Any], key: str, kind: type, zero: Any) -> Any:
    """The field `key` of the block `b`, or `zero` where it is missing or of another type."""
    value = b.get(key)
    return value if _typed(value, kind) else zero


def _text_of(blocks: List[_Block]) -> str:
    """The text of the blocks `blocks`."""
    return "\n".join(b.text for b in blocks if b.type == "text")


_COMMAND_NAME = re.compile(r"<command-name>(.*?)</command-name>")
_COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
_NOT_HUMAN = re.compile(r"<(local-command|task-notification|system-reminder)")


def _human(text: str) -> str:
    """The type of the event the text `text` of the user's turn is: prompt, command or interrupt;
    "" for what Claude Code wrote there."""
    if text.startswith("[Request interrupted by user"):
        return "interrupt"
    if text.startswith(("<command-name>", "<command-message>")):
        return "command"
    if _NOT_HUMAN.match(text) or text.startswith("Base directory for this skill:"):
        return ""
    if _trim(text):
        return "prompt"
    return ""


def _command_text(text: str) -> str:
    """The command the user typed, `/name args`, from what Claude Code wrote of it."""
    name = _COMMAND_NAME.search(text)
    args = _COMMAND_ARGS.search(text)
    return _trim((name.group(1) if name else "") + " " + (args.group(1) if args else ""))


def _response(message: Any) -> Optional[Tuple[str, int, int]]:
    """The id of the assistant's message `message`, the tokens of the context it was given and
    the tokens it wrote, from the usage Claude Code records; None without one, and for a message
    Claude Code wrote itself, such as "No response requested.", whose usage is zeros."""
    if not isinstance(message, dict):
        return None
    mid, model, usage = message.get("id"), message.get("model"), message.get("usage")
    if (mid is not None and not _typed(mid, str)) or (model is not None and not _typed(model, str)):
        return None
    if not isinstance(usage, dict) or not mid or model == "<synthetic>":
        return None
    counts = []
    keys = ["input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"]
    for key in keys + ["output_tokens"]:
        n = usage.get(key)
        if n is None:
            n = 0
        if not _typed(n, int):
            return None
        counts.append(n)
    return mid, counts[0] + counts[1] + counts[2], counts[3]


# What an image or a document counts as, in characters of text, whatever the size of its data:
# about 1,500 tokens, an estimate for a screenshot.
_IMAGE_CHARS = 6000


def _size(v: Any) -> int:
    """How many characters of text the JSON value `v` holds, so that a result, a prompt and an
    attachment are measured alike: the length of its strings, but for the names of types, with an
    image or a document counted as _IMAGE_CHARS."""
    if isinstance(v, str):
        return len(v)
    if isinstance(v, list):
        return sum(_size(e) for e in v)
    if isinstance(v, dict):
        if v.get("type") in ("image", "document"):
            return _IMAGE_CHARS
        return sum(_size(e) for k, e in v.items() if k != "type")
    return 0


def headless(entrypoint: str) -> bool:
    """Whether a session whose entrypoint, CLAUDE_CODE_ENTRYPOINT in its environment and in each
    line of its Transcript, is `entrypoint` is headless, with nobody to answer: `claude -p`'s, such
    as one run by a project's own Git hook, is sdk-cli, the Agent SDK's sdk-ts or sdk-py, and one
    with the user cli or an editor's name."""
    return entrypoint.startswith("sdk-")


_RFC3339 = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})", re.A
)


def _nanos(timestamp: str) -> Optional[int]:
    """The time `timestamp`, RFC 3339, in nanoseconds since the epoch; None when it isn't one."""
    m = _RFC3339.fullmatch(timestamp)
    if not m:
        return None
    year, month, day, hour, minute, second = (int(g) for g in m.groups()[:6])
    if not (1 <= month <= 12 and 1 <= day <= calendar.monthrange(year, month)[1]):
        return None
    if hour > 23 or minute > 59 or second > 59:
        return None
    seconds = calendar.timegm((year, month, day, hour, minute, second))
    zone = m.group(8)
    if zone != "Z":
        offset = int(zone[1:3]) * 3600 + int(zone[4:6]) * 60
        seconds -= offset if zone[0] == "+" else -offset
    return seconds * 10**9 + int((m.group(7) or "").ljust(9, "0"))


def condense(transcript: Union[str, bytes], id: str) -> Session:
    """The session of the Transcript `transcript`, whose id is `id`."""
    s = Session(id=id)
    # The tool calls by id: each by what it acts on, and its tool.
    calls: Dict[str, Tuple[str, str]] = {}
    counts: Dict[str, int] = {}
    # The last response's id, context and output, and the results given to the next one.
    prev, context, output, other = "", 0, 0, 0
    pending: List[_Result] = []
    first: Optional[int] = None
    last: Optional[int] = None
    cwd = ""
    for at, line in _lines(transcript):
        kind = _str(line, "type")
        if _str(line, "aiTitle"):
            s.title = line["aiTitle"]
        if _str(line, "cwd"):
            cwd = line["cwd"]
        if headless(_str(line, "entrypoint")):
            s.headless = True
        t = _nanos(_str(line, "timestamp"))
        if t is not None:
            if first is None or t < first:
                first = t
            if last is None or t > last:
                last = t
        bs = _blocks(line.get("message"))
        if kind == "assistant":
            got = _response(line.get("message"))
            if got is not None:
                rid, c, o = got
                if rid != prev:
                    # The context grew by the last response's output and what came after it.
                    if prev:
                        s._charge(pending, other, c - context - output)
                    prev, pending, other = rid, [], 0
                context, output = c, o
            for b in bs:
                if b.type != "tool_use" or not b.name:
                    continue
                s.tools[b.name] = s.tools.get(b.name, 0) + 1
                c = _call(b.name, b.input, cwd)
                calls[b.id] = (c, b.name)
                if b.name in _REPEATED:
                    counts[c] = counts.get(c, 0) + 1
        results = any(b.type == "tool_result" for b in bs)
        if kind == "attachment":
            other += _size(line.get("attachment"))
        elif kind == "user" and not results:
            other += _size(line.get("message"))
        if kind != "user" or line.get("isMeta"):
            continue
        if results:
            for b in bs:
                if b.type != "tool_result":
                    continue
                call, tool = calls.get(b.tool_use_id, ("?", "?"))
                pending.append(_Result(at, call, tool, _size(b.content)))
                if b.is_error:
                    text = _text_of(_content(b.content))
                    s.events.append(Event(at, "error", _kind(text), call, text))
            continue
        text = _text_of(bs)
        typ = _human(text)
        if typ == "interrupt":
            s.events.append(Event(at, typ))
        elif typ == "command":
            s.events.append(Event(at, typ, text=_command_text(text)))
        elif typ == "prompt":
            s.events.append(Event(at, typ, text=text))
    if first is not None and last is not None:
        s.start = _format(first)
        minute = 60 * 10**9
        s.minutes = (last - first + minute // 2) // minute
    s.repeats = sorted(
        (Repeat(c, n) for c, n in counts.items() if n >= _REPEAT_MIN), key=lambda r: (-r.n, r.call)
    )
    s.costs = sorted(s.costs, key=lambda c: -c.tokens)[:_TOP_COSTS]
    return s


def _format(nanos: int) -> str:
    """The time `nanos`, in nanoseconds since the epoch, as `YYYY-MM-DD hh:mm` UTC."""
    return datetime.fromtimestamp(nanos // 10**9, timezone.utc).strftime("%Y-%m-%d %H:%M")


def _kilo(n: int) -> str:
    """`n` tokens in thousands, `12k`."""
    return f"{(n + 500) // 1000}k"


# The kinds of a failed tool call, by its error; the first that matches names it.
_KINDS: List[Tuple[str, "re.Pattern[str]"]] = [
    ("check", re.compile(r"hook error: " + names.PLUGIN + r":[a-z-]+: ")),
    ("rejected", re.compile(r"doesn't want to proceed|User rejected")),
    ("hook", re.compile(r"hook error")),
    ("classifier", re.compile(r"auto mode classifier|auto mode cannot")),
    (
        "permission",
        re.compile(
            r"requires? approval|[Pp]ermission to use .* (denied|has been denied)|"
            r"was blocked\. For security"
        ),
    ),
    ("stale", re.compile(r"modified since read|has not been read yet")),
    ("exit", re.compile(r"Exit code [0-9]+")),
]


def _kind(error: str) -> str:
    """The kind of a tool call that failed with `error`."""
    for kind, pattern in _KINDS:
        if (pattern.match if kind == "exit" else pattern.search)(error):
            return kind
    return "other"


# The inputs that say what a tool call acts on, the likeliest first.
_CALL_KEYS = ["command", "file_path", "path", "pattern", "skill", "url", "description"]


def _call(name: str, input: Dict[str, Any], cwd: str) -> str:
    """A tool call by what it acts on, a path from the folder `cwd` where it is in it:
    `Bash(go test ./...)`, `Read(src/x.go)`."""
    text = ""
    for key in _CALL_KEYS + sorted(input):
        if _typed(input.get(key), str):
            text = input[key]
            break
    if cwd and text.startswith(cwd + "/"):
        text = text[len(cwd) + 1 :]
    return name + "(" + text + ")"


def _clip(text: str, most: int) -> str:
    """`text` on one line, cut to `most` characters."""
    flat = " ".join(_fields(text))
    if len(flat) > most:
        return flat[: most - 1] + "…"
    return flat


def _gist(e: Event, most: int) -> str:
    """The failure's error, cut to `most` characters: for a failed command, its end, where its own
    error usually is."""
    if e.kind != "exit":
        return _clip(e.text, most)
    code, _, rest = e.text.partition("\n")
    tail = " ".join(_fields(rest))
    if len(tail) > most:
        return code + ": …" + tail[len(tail) - most :]
    return code + ": " + tail


_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(-----END [A-Z ]*KEY-----|\Z)", re.S
)
# A long run of the characters a token is made of: an API key, a JWT's part.
_TOKEN = re.compile(r"[A-Za-z0-9_+-]{32,}")
_LETTER = re.compile(r"[A-Za-z]")
_DIGIT = re.compile(r"[0-9]")
_HEX = re.compile(r"[0-9a-fA-F-]+")


def mask(text: str) -> str:
    """`text` with anything that may be a Secret replaced by `*****`: a private key's block, each
    kind of Secret no-secrets-in-commits knows, and a long run of letters and digits mixed, but not
    hex, such as a commit or a session's id (ADR transcripts)."""
    stars = "*****"
    text = _PRIVATE_KEY.sub(lambda _: stars, text)
    text = checks.mask_secrets(text, stars)

    def token(m: "re.Match[str]") -> str:
        s = m.group()
        if _LETTER.search(s) and _DIGIT.search(s) and not _HEX.fullmatch(s):
            return stars
        return s

    return _TOKEN.sub(token, text)


_PROMPT_MIN = 20  # shorter prompts ("yes", "commit it") repeat without meaning much
_TOP = 5  # the commonest failures of each kind shown
_TOP_PROMPTS = 10


class _Seen:
    """How often one failure or prompt came up, and in which sessions."""

    def __init__(self, key: str, id: str):
        self.key = key
        self.n = 1
        self.ids = {id}


def _tally(counts: List[_Seen], key: str, id: str) -> None:
    """Adds `key` of the session `id` to `counts`, in the order keys first come."""
    for c in counts:
        if c.key == key:
            c.n += 1
            c.ids.add(id)
            return
    counts.append(_Seen(key, id))


def _commonest(counts: List[_Seen]) -> List[_Seen]:
    """`counts` by how often each came up, keeping the first seen first among equals."""
    return sorted(counts, key=lambda c: -c.n)


def summary(sessions: List[Session]) -> str:
    """The sessions `sessions` together, for a Retro, masked: their failures by kind, with the
    commonest of each (a failed command, a call rejected or refused by the classifier, by its tool;
    the rest by their error), then the prompts typed more than once, which a skill or a Hook could
    take over, then the tools whose calls added the most tokens to the context."""
    order: List[str] = []
    by_kind: Dict[str, List[_Seen]] = {}
    prompts: List[_Seen] = []
    tokens: Dict[str, int] = {}
    seen_in: Dict[str, int] = {}
    for s in sessions:
        for tool, n in s.tokens.items():
            tokens[tool] = tokens.get(tool, 0) + n
            seen_in[tool] = seen_in.get(tool, 0) + 1
        for e in s.events:
            if e.type == "error":
                key = _clip(e.text, 100)
                if e.kind in ("exit", "rejected", "classifier"):
                    key = e.call.partition("(")[0]
                if e.kind not in by_kind:
                    order.append(e.kind)
                    by_kind[e.kind] = []
                _tally(by_kind[e.kind], key, s.id)
            elif e.type == "prompt":
                text = _clip(e.text.lower(), 100)
                if len(text.encode()) >= _PROMPT_MIN:
                    _tally(prompts, text, s.id)

    def total(kind: str) -> int:
        return sum(c.n for c in by_kind[kind])

    order.sort(key=lambda kind: -total(kind))
    out = [f"# Across {len(sessions)} sessions"]
    for kind in order:
        out.append(f"{kind}: {total(kind)}")
        for c in _commonest(by_kind[kind])[:_TOP]:
            out.append(f"  {c.n}× in {len(c.ids)} session(s): {c.key}")
    repeats = [f"  {c.n}× {c.key}" for c in _commonest(prompts) if c.n > 1][:_TOP_PROMPTS]
    if repeats:
        out.append("repeated prompts:")
        out.extend(repeats)
    costliest = sorted(tokens, key=lambda tool: (-tokens[tool], tool))
    if costliest:
        out.append("tokens added to the context, by tool:")
        for tool in costliest[:_TOP]:
            out.append(f"  {tool} {_kilo(tokens[tool])} in {seen_in[tool]} session(s)")
    return mask("\n".join(out))


# The most of one block around shows.
_AROUND_CHARS = 2000


def around(transcript: Union[str, bytes], at: int, radius: int) -> str:
    """The lines of the Transcript `transcript` within `radius` of its line `at`, numbered as in a
    report: their text, tool calls and results, each cut to _AROUND_CHARS, masked. It is what a
    Retro reads instead of the raw Transcript, so a Secret an earlier session printed doesn't reach
    one more context (ADR transcripts)."""
    out: List[str] = []
    cwd = ""
    for n, line in _lines(transcript):
        if _str(line, "cwd"):
            cwd = line["cwd"]
        if n < at - radius:
            continue
        if n > at + radius:
            break
        head = f"[{n}] {_str(line, 'type')}"
        for b in _blocks(line.get("message")):
            if b.type == "text" and _trim(b.text):
                out.append(head + ": " + b.text[:_AROUND_CHARS])
            elif b.type == "tool_use":
                out.append(head + " calls " + _call(b.name, b.input, cwd))
            elif b.type == "tool_result":
                failed = " (failed)" if b.is_error else ""
                text = _text_of(_content(b.content))
                out.append(head + " result" + failed + ": " + text[:_AROUND_CHARS])
    return mask("\n".join(out))


def conversation(transcript: Union[str, bytes], most: int) -> str:
    """The user's and Claude's text in the Transcript `transcript`, for a Session review, masked,
    then cut to its last `most` characters: no tool call or result, and of what Claude Code wrote
    in the user's turn only the commands (ADR session-review)."""
    out: List[str] = []
    for _, line in _lines(transcript):
        kind = _str(line, "type")
        text = _text_of(_blocks(line.get("message")))
        if kind == "assistant" and _trim(text):
            pass
        elif kind != "user" or line.get("isMeta"):
            continue
        elif _human(text) == "prompt":
            pass
        elif _human(text) == "command":
            text = _command_text(text)
        else:
            continue
        out.append(kind + ": " + text)
    text = mask("\n\n".join(out))
    return text[len(text) - most :] if len(text) > most else text


# What Claude Code turns into `-` in the name of a project's folder of Transcripts.
_NOT_LETTER_OR_DIGIT = re.compile(r"[^A-Za-z0-9]")


def transcripts_folder(config: str, cwd: str) -> str:
    """The folder of the Transcripts of the project at `cwd`, or of the nearest folder above it
    that has one, in Claude Code's config folder `config`; "" when none has."""
    folder = os.path.normpath(cwd)
    while True:
        path = os.path.join(config, "projects", _NOT_LETTER_OR_DIGIT.sub("-", folder))
        if os.path.isdir(path):
            return path
        parent = os.path.dirname(folder) or "."
        if parent == folder:
            return ""
        folder = parent


def read(path: str) -> Session:
    """The session of the Transcript file `path`, named after it; OSError when it can't be read."""
    with open(path, "rb") as f:
        text = f.read()
    name = os.path.basename(path)
    return condense(text, name[: -len(".jsonl")] if name.endswith(".jsonl") else name)


def latest(folder: str, n: int) -> List[Session]:
    """The `n` latest sessions in the folder `folder` worth a Retro, newest first: not headless,
    and something besides /clear was typed or failed."""
    try:
        paths = [os.path.join(folder, e) for e in os.listdir(folder) if e.endswith(".jsonl")]
    except OSError:
        return []

    def changed(path: str) -> float:
        try:
            return os.stat(path).st_mtime
        except OSError:
            return float("-inf")

    paths.sort(key=changed, reverse=True)
    sessions: List[Session] = []
    for path in paths:
        if len(sessions) == n:
            break
        s = read(path)
        if s.worth():
            sessions.append(s)
    return sessions


_CLEAR = re.compile(r"/clear\b", re.A)

