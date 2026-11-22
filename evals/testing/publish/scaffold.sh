#!/bin/bash
# A small blog library on the standard library alone, whose store is SQLite in a file the caller
# names: a test can run it for real in a temp folder, and the clock is the one thing it can't own.
set -euo pipefail
git init -q -b main
mkdir -p src/blog tests
cat > README.md <<'R'
# blog

Publishes posts to a SQLite store. Tests: `/usr/bin/python3 -m unittest` from the repo's root.
R
cat > src/blog/__init__.py <<'R'
"""Publishes posts to a SQLite store."""
R
cat > src/blog/store.py <<'R'
"""The posts' store: SQLite in a file the caller names."""

import sqlite3
from typing import Optional


class Store:
    """Keeps posts by slug in the SQLite file at `path`."""

    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS posts"
            " (slug TEXT PRIMARY KEY, title TEXT, body TEXT, published_at REAL)"
        )

    def save(self, slug: str, title: str, body: str, published_at: float) -> None:
        """Saves a post; a slug already saved raises sqlite3.IntegrityError."""
        with self._db:
            self._db.execute(
                "INSERT INTO posts VALUES (?, ?, ?, ?)", (slug, title, body, published_at)
            )

    def get(self, slug: str) -> Optional[dict]:
        """Returns the post with the slug as a dict, or None."""
        row = self._db.execute(
            "SELECT slug, title, body, published_at FROM posts WHERE slug = ?", (slug,)
        ).fetchone()
        if row is None:
            return None
        return dict(zip(("slug", "title", "body", "published_at"), row))
R
cat > src/blog/posts.py <<'R'
"""Publishing posts."""
R
cat > tests/__init__.py <<'R'
R
cat > tests/test_store.py <<'R'
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blog.store import Store  # noqa: E402


class StoreTest(unittest.TestCase):
    def test_reads_back_a_saved_post(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(os.path.join(tmp, "blog.db"))
            store.save("hello", "Hello", "Hi.", 1700000000.0)
            self.assertEqual(store.get("hello")["title"], "Hello")
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Start the blog library"
