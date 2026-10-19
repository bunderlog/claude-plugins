---
description: A decision that changes an earlier one is recorded by editing that ADR in place, the old choice kept under Considered options with when it held until.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

We talked it over with the payments team: an order must be accepted only once its payment is
confirmed, so OrderService will call BillingClient.charge() directly when an order is placed, and
fail the order when the charge fails. Shipping still starts on the OrderPaid event. We're agreed,
record the decision; don't change the code yet.
