"""Reads the subset of YAML a Config is written in, with the standard library alone (ADR config):
block maps and lists, flow maps and lists, plain and quoted scalars, and comments. What is outside
it, such as an anchor, a tag or a block scalar, is an Error, as YAML that doesn't parse is. Only the
first document is read."""

from __future__ import annotations

import bisect
import re
from typing import List, Optional, Tuple


class Error(Exception):
    """Why a text isn't YAML of the subset, at line `line`."""

    def __init__(self, line: int, text: str):
        super().__init__(f"line {line}: {text}")
        self.line = line
        self.text = text


class Node:
    """A map, a list or a scalar, at line `line`, from 1.

    A scalar's `tag` is null, bool, int, float or str, as YAML 1.2's core schema resolves it, and
    `text` is what it says; a map's tag is map and its `pairs` are its keys and values in order; a
    list's tag is seq and its `items` are its values."""

    def __init__(
        self,
        tag: str,
        line: int,
        text: str = "",
        pairs: Optional[List[Tuple[Node, Node]]] = None,
        items: Optional[List[Node]] = None,
    ):
        self.tag = tag
        self.line = line
        self.text = text
        self.pairs = pairs or []
        self.items = items or []

    @property
    def value(self):
        """The node as Python's None, bool, int, float, str, dict or list."""
        if self.tag == "map":
            return {k.text: v.value for k, v in self.pairs}
        if self.tag == "seq":
            return [item.value for item in self.items]
        if self.tag == "null":
            return None
        if self.tag == "bool":
            return self.text.lower() == "true"
        if self.tag == "int":
            return int(self.text, 0 if self.text[:2] in ("0o", "0x") else 10)
        if self.tag == "float":
            return float(self.text.lower().replace(".inf", "inf").replace(".nan", "nan"))
        return self.text

    def __repr__(self) -> str:
        return f"Node({self.tag}, line {self.line}, {self.value!r})"


def parse(text: str) -> Optional[Node]:
    """The first document of `text`, or None where it has none: it is empty, or only comments."""
    lines = _lines(text)
    if not lines:
        return None
    p = _Parser(lines)
    node = p.block(lines[0][1])
    if p.i < len(lines):
        n, indent, _ = lines[p.i]
        raise Error(n, "unexpected indentation" if indent != lines[0][1] else "unexpected text")
    return node


# A line with something on it: its number, its indent and its text after the indent, without its
# comment.
_Line = Tuple[int, int, str]


def _lines(text: str) -> List[_Line]:
    out: List[_Line] = []
    for n, raw in enumerate(text.lstrip("\N{BYTE ORDER MARK}").splitlines(), 1):
        body = raw.lstrip(" ")
        indent = len(raw) - len(body)
        body = _uncomment(body).rstrip()
        if not body:
            continue
        if body[0] == "\t":
            raise Error(n, "found a tab character that violates indentation")
        if indent == 0 and body == "---":
            if out:
                break  # a second document
            continue
        if indent == 0 and body == "...":
            break
        if indent == 0 and body[0] == "%":
            raise Error(n, "a directive is not supported")
        out.append((n, indent, body))
    return out


def _uncomment(body: str) -> str:
    """`body` without its comment: from a `#` at its start or after a space, outside quotes. A
    quote opens a quoted scalar only where a scalar may start, so `echo don't` stays plain."""
    quote = ""
    i = 0
    while i < len(body):
        c = body[i]
        if quote == "'":
            if c == "'":
                if body[i + 1 : i + 2] == "'":
                    i += 1
                else:
                    quote = ""
        elif quote == '"':
            if c == "\\":
                i += 1
            elif c == '"':
                quote = ""
        elif c == "#" and (i == 0 or body[i - 1] in " \t"):
            return body[:i]
        elif c in "'\"" and _scalar_starts(body, i):
            quote = c
        i += 1
    return body


def _scalar_starts(body: str, i: int) -> bool:
    before = body[:i].rstrip(" \t")
    return (i == 0 or body[i - 1] in " \t[{,") and (not before or before[-1] in ":-[{,?")


def _is_item(body: str) -> bool:
    return body == "-" or body.startswith(("- ", "-\t"))


_UNSUPPORTED = {
    "&": "an anchor",
    "*": "an alias",
    "!": "a tag",
    "|": "a block scalar",
    ">": "a block scalar",
    "?": "a complex key",
}


class _Parser:
    """Parses the block structure of `lines`, from line `i` on."""

    def __init__(self, lines: List[_Line]):
        self.lines = lines
        self.i = 0

    def block(self, indent: int) -> Node:
        """The value whose first line is line i, at `indent`."""
        n, _, body = self.lines[self.i]
        if _is_item(body):
            return self.seq(indent)
        if _split_key(body, n) is not None:
            return self.map(indent)
        return self.value(body, n)

    def map(self, indent: int) -> Node:
        line = self.lines[self.i][0]
        pairs: List[Tuple[Node, Node]] = []
        seen = {}
        while self.i < len(self.lines):
            n, ind, body = self.lines[self.i]
            if ind < indent:
                break
            if ind > indent:
                raise Error(n, "unexpected indentation")
            split = _split_key(body, n)
            if split is None:
                raise Error(n, "did not find expected key")
            key, rest = split
            if key.text in seen:
                raise Error(n, f'mapping key "{key.text}" already defined at line {seen[key.text]}')
            seen[key.text] = n
            if rest:
                value = self.value(rest, n)
            else:
                self.i += 1
                value = self.nested(indent, n, list_at_indent=True)
            pairs.append((key, value))
        return Node("map", line, pairs=pairs)

    def seq(self, indent: int) -> Node:
        line = self.lines[self.i][0]
        items: List[Node] = []
        while self.i < len(self.lines):
            n, ind, body = self.lines[self.i]
            if ind < indent or (ind == indent and not _is_item(body)):
                break
            if ind > indent:
                raise Error(n, "unexpected indentation")
            rest = body[1:].lstrip(" \t")
            if not rest:
                self.i += 1
                items.append(self.nested(indent, n, list_at_indent=False))
                continue
            if _is_item(rest):
                raise Error(n, "a list inside a list on one line is not supported")
            if _split_key(rest, n) is not None:
                raise Error(n, "a map inside a list is not supported")
            items.append(self.value(rest, n))
        return Node("seq", line, items=items)

    def nested(self, indent: int, n: int, list_at_indent: bool) -> Node:
        """The value under a key or an item at `indent` with nothing after it on line `n`: the
        lines below indented more, a list at the same indent under a key, or else null."""
        if self.i < len(self.lines):
            _, ind, body = self.lines[self.i]
            if ind > indent:
                return self.block(ind)
            if ind == indent and list_at_indent and _is_item(body):
                return self.seq(ind)
        return Node("null", n)

    def value(self, rest: str, n: int) -> Node:
        """The value `rest`, the end of line i, at line `n`; a flow map or list may go on over the
        lines below."""
        if rest[0] not in "[{":
            self.i += 1
            return _block_scalar(rest, n)
        segments = [(n, rest)] + [(m, body) for m, _, body in self.lines[self.i + 1 :]]
        flow = _Flow(segments)
        node = flow.node()
        end = flow.line()
        flow.ws(newlines=False)
        if flow.peek() not in ("", "\n"):
            raise Error(end, "unexpected text after " + ("]" if rest[0] == "[" else "}"))
        while self.i < len(self.lines) and self.lines[self.i][0] <= end:
            self.i += 1
        return node


def _split_key(body: str, n: int) -> Optional[Tuple[Node, str]]:
    """The key of the map entry `body` at line `n`, and what follows its colon, or None where
    `body` isn't one."""
    if body[0] in "'\"":
        text, end = _quoted(body, 0, n)
        after = body[end:].lstrip(" \t")
        if after[:1] == ":" and after[1:2] in ("", " ", "\t"):
            return Node("str", n, text), after[1:].strip(" \t")
        return None
    if body[0] in "[{":
        return None
    for m in re.finditer(":", body):
        if body[m.end() : m.end() + 1] in ("", " ", "\t"):
            key = body[: m.start()].rstrip(" \t")
            if not key:
                raise Error(n, "did not find expected key")
            return _resolve(key, n), body[m.end() :].strip(" \t")
    return None


def _block_scalar(rest: str, n: int) -> Node:
    """The scalar `rest` that ends line `n`, outside a flow map or list."""
    if rest[0] in "'\"":
        text, end = _quoted(rest, 0, n)
        if rest[end:].strip(" \t"):
            raise Error(n, "unexpected text after a quoted value")
        return Node("str", n, text)
    if _is_item(rest):
        raise Error(n, "block sequence entries are not allowed in this context")
    if rest[0] in _UNSUPPORTED:
        raise Error(n, _UNSUPPORTED[rest[0]] + " is not supported")
    if rest[0] in "@`":
        raise Error(n, "found character that cannot start any token")
    if re.search(r":(\s|$)", rest):
        raise Error(n, "mapping values are not allowed in this context")
    return _resolve(rest, n)


_NULL = {"", "~", "null", "Null", "NULL"}
_BOOL = {"true", "True", "TRUE", "false", "False", "FALSE"}
_INT = re.compile(r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+")
_FLOAT = re.compile(
    r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN)"
)


def _resolve(text: str, n: int) -> Node:
    """The plain scalar `text` at line `n`, tagged as YAML 1.2's core schema resolves it."""
    if text in _NULL:
        return Node("null", n, text)
    if text in _BOOL:
        return Node("bool", n, text)
    if _INT.fullmatch(text):
        return Node("int", n, text)
    if _FLOAT.fullmatch(text):
        return Node("float", n, text)
    return Node("str", n, text)


_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
    "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85", "_": "\xa0",
    "L": " ", "P": " ",
}
_HEX = {"x": 2, "u": 4, "U": 8}


def _quoted(s: str, start: int, n: int) -> Tuple[str, int]:
    """The quoted scalar that starts at `start` of `s`, at line `n`, and the index after its
    closing quote; it must close on its line."""
    quote = s[start]
    out = []
    i = start + 1
    while i < len(s) and s[i] != "\n":
        c = s[i]
        if quote == "'" and c == "'":
            if s[i + 1 : i + 2] != "'":
                return "".join(out), i + 1
            out.append("'")
            i += 2
            continue
        if quote == '"' and c == '"':
            return "".join(out), i + 1
        if quote == '"' and c == "\\":
            e = s[i + 1 : i + 2]
            if e in _HEX:
                digits = s[i + 2 : i + 2 + _HEX[e]]
                if len(digits) != _HEX[e] or not re.fullmatch("[0-9a-fA-F]+", digits):
                    raise Error(n, "did not find expected hexadecimal number")
                out.append(chr(int(digits, 16)))
                i += 2 + _HEX[e]
                continue
            if e not in _ESCAPES:
                raise Error(n, "found unknown escape character while parsing a quoted scalar")
            out.append(_ESCAPES[e])
            i += 2
            continue
        out.append(c)
        i += 1
    raise Error(n, "found unexpected end of line while parsing a quoted scalar")


# A plain scalar in a flow map or list ends at a flow indicator, a colon before a space or one, or
# the end of its line.
_FLOW_PLAIN = re.compile(r"[^,\[\]{}\n]*?(?=:[\s,\[\]{}]|:$|[,\[\]{}\n]|$)")


class _Flow:
    """Parses a flow map or list over the lines `segments`, each a line's number and its text."""

    def __init__(self, segments: List[Tuple[int, str]]):
        self.text = "\n".join(text for _, text in segments)
        self.numbers = [n for n, _ in segments]
        self.starts = []
        at = 0
        for _, text in segments:
            self.starts.append(at)
            at += len(text) + 1
        self.pos = 0

    def line(self) -> int:
        return self.numbers[bisect.bisect_right(self.starts, self.pos) - 1]

    def peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def ws(self, newlines: bool = True) -> None:
        while self.peek() in (" ", "\t") or (newlines and self.peek() == "\n"):
            self.pos += 1

    def node(self) -> Node:
        self.ws()
        c = self.peek()
        if c == "[":
            return self.seq()
        if c == "{":
            return self.map()
        line = self.line()
        if c in ("'", '"'):
            text, self.pos = _quoted(self.text, self.pos, line)
            return Node("str", line, text)
        if c in _UNSUPPORTED:
            raise Error(line, _UNSUPPORTED[c] + " is not supported")
        if c in ("@", "`"):
            raise Error(line, "found character that cannot start any token")
        text = _FLOW_PLAIN.match(self.text, self.pos).group().rstrip(" \t")
        if not text:
            raise Error(line, "did not find expected node content")
        node = _resolve(text, line)
        self.pos += len(text)
        return node

    def seq(self) -> Node:
        line = self.line()
        self.pos += 1
        items: List[Node] = []
        while True:
            self.ws()
            if self.peek() == "]":
                self.pos += 1
                return Node("seq", line, items=items)
            items.append(self.node())
            self.ws()
            if self.peek() == ":":
                raise Error(self.line(), "a map inside a list is not supported")
            if self.peek() == ",":
                self.pos += 1
            elif self.peek() != "]":
                raise Error(self.line(), "did not find expected ',' or ']'")

    def map(self) -> Node:
        line = self.line()
        self.pos += 1
        pairs: List[Tuple[Node, Node]] = []
        seen = {}
        while True:
            self.ws()
            if self.peek() == "}":
                self.pos += 1
                return Node("map", line, pairs=pairs)
            key = self.node()
            if key.tag in ("map", "seq"):
                raise Error(key.line, "a map or a list as a key is not supported")
            if key.text in seen:
                raise Error(
                    key.line, f'mapping key "{key.text}" already defined at line {seen[key.text]}'
                )
            seen[key.text] = key.line
            self.ws()
            value = Node("null", key.line)
            if self.peek() == ":":
                self.pos += 1
                self.ws()
                if self.peek() not in (",", "}"):
                    value = self.node()
                    self.ws()
            pairs.append((key, value))
            if self.peek() == ",":
                self.pos += 1
            elif self.peek() != "}":
                raise Error(self.line(), "did not find expected ',' or '}'")
