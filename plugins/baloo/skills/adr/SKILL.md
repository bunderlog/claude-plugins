---
name: adr
description: Challenge and record the project's decisions — while designing, or when the user asks to record or write down a decision — a business rule, boundary, ownership, integration, naming or technology choice being made or revisited, or a proposal that may contradict an earlier decision. Checks against the project's ADRs in .about/adr/ (offering to move numbered ones there), surfaces implicit decisions, probes alternatives and cost, and writes an ADR when a decision is hard to reverse, not obvious without an explanation, and a real trade-off. Not for merely reading ADRs for context.
---

# ADR

You are shaping the project's decisions, not just writing them down. Make each one explicit
and justified; don't just agree.

## Files

`.about/adr/<subject>.md` at the git repo's root — one subject per file, its decisions as they
stand now ([format](format.md)), never numbered; create the folder with the first ADR. Read the
existing titles and the items in `.about/inbox.md` before you start.

If the project also keeps numbered ADRs (`docs/adr/`, `doc/adr/`, `docs/decisions/`), read them
as decisions too, and offer once to move them all into `.about/adr/`: one file per subject, a
superseded decision under Considered options. Say what the move breaks: the numbers cited in code,
commits and other repos, and the tool that keeps them (adr-tools, log4brains). Move them only if
the user agrees; either way, write a new decision to `.about/adr/<subject>.md`.

## Check

Before accepting a proposal, look for an ADR it contradicts and call it out: "ADR ordering says
Ordering talks to Billing by events — this adds a direct call. Follow it, or change it?"
Never contradict an ADR silently. If the topic touches an item in the Inbox, settle it now.

## Surface

Design talk decides things implicitly. When a rule, boundary, ownership, integration or
technology choice settles, name it: "So we're deciding X over Y — right?"

## Probe

Before a decision is accepted:
- What are the real alternatives, and why this one?
- What does it cost or rule out? Who or what depends on it?
- How hard is it to reverse, and what would make us revisit it?

Test it against concrete cases: "Billing is down when `OrderPlaced` is sent — is the order
paid or not?" Reach for:
- failure: a dependency is down or slow; the process fails halfway
- twice or out of order: retries, duplicates, concurrent actors
- time: expiry, time zones, back-dated changes
- growth: 10–100× load, data or users
- trust: who can reach it (an anonymous caller, another tenant, crafted input), and what could
  they do with it?
- the exception: which real case will be first to want to break this rule?
- what already exists: data and clients built the old way — migrate them, or support both?

Check the code as well: a decision the code already contradicts is the most valuable finding —
"You said Ordering calls Billing only through events, but `OrderService` calls
`BillingClient.charge()` directly. Is the decision wrong, or is the code?" A case with no answer
is a finding — don't paper over it: raise it, and if it stays open, record it in the Inbox.
Ask a few pointed questions at a time, not a questionnaire.

A decision the user says is already agreed gets recorded first: write it, then in the same reply
name the ADR it overturns and the questions the probe raises, and put one still open into the
Inbox.

## Record

Write an ADR only when all three hold — otherwise the conversation is the record:
1. **Hard to reverse** — changing course later is costly.
2. **Not obvious without an explanation** — someone who wasn't in the discussion would ask
   "why this way?" or take it for a mistake and "fix" it.
3. **A real trade-off** — genuine alternatives existed and one won for stated reasons.

When the user asks to record a decision that fails one of them, write none and tell them in one
line which one fails: "No ADR: the retry count is one constant, easy to change back."

- A decision goes into the ADR on its subject, a new file only for a new subject. Still open →
  an item in `.about/inbox.md` with the options: a `## <title>`, a line `<YYYY-MM-DD> · adr`,
  then what it is and what would settle it. Once settled, write the decision taken ("we won't do
  X" is a decision too) into the ADR on its subject and delete the item, and the file with its
  last one.
- An ADR says what holds now. When a decision changes, edit it in place and update the Date;
  git keeps the earlier text. The choice it drops moves to Considered options, marked
  `(until <date>)` with why, so nobody proposes it again unwarned.
- Tell the user in one line what changed.
