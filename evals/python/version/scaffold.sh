#!/bin/bash
# A small library that posts notifications to a webhook, for Python 3.9 and later, whose client
# has type hints but no `from __future__ import annotations` and no typing imports: a new optional
# parameter written `float | None` fails there on import.
set -euo pipefail
git init -q -b main
mkdir -p src/notify
cat > pyproject.toml <<'R'
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "notify"
version = "0.3.0"
description = "Posts notifications to a webhook"
requires-python = ">=3.9"
dependencies = []
R
cat > README.md <<'R'
# notify

Posts notifications to a webhook.

    from notify.client import send
    send("https://hooks.example.com/abc", {"text": "Deployed"})
R
cat > src/notify/__init__.py <<'R'
"""Posts notifications to a webhook."""
R
cat > src/notify/client.py <<'R'
"""The webhook's client."""

import json
import urllib.request


def send(url: str, body: dict) -> int:
    """Posts `body` as JSON to `url` and returns the response's status."""
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request) as response:
        return response.status
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Start the notify library"
