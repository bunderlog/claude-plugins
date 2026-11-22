---
description: New behavior starts with its test, seen red before the code that turns it green.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 40
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

Add `publish(store, title, body)` to `src/blog/posts.py`: it makes the post's slug from its title
(lowercase, words joined by `-`, anything else dropped), saves the post in the store with the time
it was published, and returns the slug; a title that makes an empty slug raises `ValueError`, and
so does a slug the store already has. Write its tests in `tests/test_posts.py`, run with
`/usr/bin/python3 -m unittest`.
