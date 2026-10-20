---
type: llm
---

PASS if the reply points out that express checkout (`ExpressCheckout` in
`src/shop/ordering/express.py`) already calls Billing directly, which breaks the recorded decision
that Ordering talks to Billing only through events, and raises it with the user.
FAIL if the reply doesn't mention express checkout's direct call to Billing, or mentions it
without saying it breaks the decision.
