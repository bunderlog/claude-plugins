"""louie's MCP server, `code-host`, over stdio: one JSON-RPC message a line on stdin, each answer a
line on stdout, the tools themselves in codehost (ADR code-host). Logs go nowhere: stdout carries
only the protocol."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Mapping, Optional, TextIO

from louie import codehost, version

# The protocol versions the server speaks, the newest last; it answers a client's own when it is
# one of these, else the newest, as MCP's lifecycle has it.
VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
NAME = "code-host"

Call = Callable[[str, Mapping[str, Any]], Dict[str, Any]]


def serve(stdin: TextIO, stdout: TextIO, call: Optional[Call] = None) -> int:
    """Answers each message on `stdin` until it ends, and returns 0."""
    tool = call or (lambda name, params: codehost.call(name, params))
    for line in stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except ValueError:
            _write(stdout, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        if not isinstance(message, dict):
            _write(stdout, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
            continue
        reply = _answer(message, tool)
        if reply is not None:
            _write(stdout, reply)
    return 0


def _answer(message: Dict[str, Any], tool: Call) -> Optional[Dict[str, Any]]:
    """The reply to one message, or None for a notification, which gets none."""
    if "id" not in message:
        return None
    method = message.get("method")
    params = message.get("params") or {}
    if not isinstance(params, dict):
        return _error(message, -32602, "params must be an object")
    if method == "initialize":
        asked = params.get("protocolVersion")
        result = {
            "protocolVersion": asked if asked in VERSIONS else VERSIONS[-1],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": NAME, "version": version.read()},
        }  # type: Dict[str, Any]
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [
            {"name": name, "description": t["description"],
             "inputSchema": {"type": "object", "properties": t["properties"], "required": t["required"]}}
            for name, t in codehost.TOOLS.items()
        ]}
    elif method == "tools/call":
        name = params.get("name", "")
        if name not in codehost.TOOLS:
            return _error(message, -32602, "no tool %r" % name)
        try:
            answer = tool(name, params.get("arguments") or {})
        except Exception as e:  # noqa: BLE001 - the server must answer and live on
            answer = {"error": "internal", "message": type(e).__name__}
        result = {"content": [{"type": "text", "text": json.dumps(answer)}], "isError": "error" in answer}
    else:
        return _error(message, -32601, "method not found: %s" % method)
    return {"jsonrpc": "2.0", "id": message["id"], "result": result}


def _error(message: Dict[str, Any], code: int, text: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": code, "message": text}}


def _write(stdout: TextIO, reply: Dict[str, Any]) -> None:
    stdout.write(json.dumps(reply) + "\n")
    stdout.flush()
