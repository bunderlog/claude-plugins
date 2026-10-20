---
description: A question left open is an item in .about/inbox.md with its options, not an ADR.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We couldn't settle what a failed charge does to an order: finance wants it cancelled at once,
support wants Billing to keep retrying for a day first. We'll ask the payments team next week.
Write it down so it doesn't get lost; don't change the code.
