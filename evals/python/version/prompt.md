---
description: Code runs on the oldest Python the project supports, so a new parameter's type is written in a form that Python evaluates there.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Write, Edit]
---

Give `send` in `src/notify/client.py` an optional `timeout`, the seconds to wait for the webhook
before giving up. Without one, it waits as it does now. No tests yet.
