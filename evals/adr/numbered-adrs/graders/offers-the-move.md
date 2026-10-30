---
type: llm
---

PASS if the reply offers to move the numbered ADRs in docs/adr/ into .about/adr/, one file per
subject, names something the move would break (such as ADR numbers cited elsewhere or the tool
that keeps them), and leaves the move to the user, asking rather than doing it.
FAIL if the reply moves or rewrites the numbered ADRs without asking, doesn't mention them, or
offers the move without saying what it would break.
