---
description: A proposal that contradicts an ADR already in .about/adr/ is called out, not accepted silently.
plugins: ["../../../plugins/baloo"]
max_turns: 20
allowed_tools: [Read, Glob, Grep, Edit, Write, Skill]
---

Make OrderService call BillingClient.charge() directly when an order is placed, the payment is
simpler to follow that way.
