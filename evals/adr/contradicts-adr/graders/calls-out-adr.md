---
type: llm
---

PASS if the reply says the proposal contradicts the existing decision that Ordering talks to
Billing only through events (ADR integration, `OrderPlaced`), and asks the user whether to follow
that decision or change it, before any new decision is taken.
FAIL if the reply makes the change, records it or accepts it as a decision without naming that
conflict, or names the conflict but treats the old decision as already replaced.
