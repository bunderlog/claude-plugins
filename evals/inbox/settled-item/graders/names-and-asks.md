---
type: llm
---

PASS if the reply says the item about Ordering calling Billing directly is already settled by the
decision that Ordering talks to Billing only through events (ADR integration), and asks the user
what to do about the carrier item, giving a recommended answer, without picking the carrier
itself.
FAIL if the reply keeps the Billing item as open, doesn't say what settles it, picks DHL or FedEx
as decided, or asks about the carrier without recommending anything.
