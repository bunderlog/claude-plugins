---
description: Code that already breaks an ADR is raised while discussing a design that touches it.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill]
---

We want gift cards: when an order is placed, the gift card's balance pays first and Billing
charges only the rest. How should this fit into ordering and billing as they are?
