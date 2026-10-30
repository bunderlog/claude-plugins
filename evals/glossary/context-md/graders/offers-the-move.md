---
type: llm
---

PASS if the reply offers to move the vocabulary in CONTEXT.md into .about/glossary.md, names
something the move would break (such as links to CONTEXT.md or a tool that reads it), and leaves
the move to the user, asking rather than doing it.
FAIL if the reply moves or rewrites CONTEXT.md without asking, doesn't mention it, or offers the
move without saying what it would break.
