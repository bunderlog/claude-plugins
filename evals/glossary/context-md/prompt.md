---
description: A project that keeps its vocabulary in CONTEXT.md gets a new term in .about/glossary.md, not in CONTEXT.md, and is offered to move CONTEXT.md.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We settled it with finance: a Refund is money returned to the customer for a paid Order, in whole
or in part, and it is never a negative Charge. Record that in the glossary; don't change the code.
