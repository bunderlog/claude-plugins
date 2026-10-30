---
description: A project that numbers its ADRs in docs/adr/ gets its new decision in .about/adr/<subject>.md, not a next numbered file, and is offered to move the numbered ADRs.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We compared Stripe and Adyen for payments with finance: Stripe's fees are higher, but its SCA
handling and its test mode saved us weeks, and switching later means migrating every saved card.
We go with Stripe. Record the decision; don't change the code.
