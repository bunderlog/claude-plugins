---
description: A decision that is easy to reverse and needs no explanation gets no ADR, and the user is told why.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Decision: in the new refund code the helper that formats an amount for logs is called
`format_cents`, not `fmt_amount`. Record the decision.
