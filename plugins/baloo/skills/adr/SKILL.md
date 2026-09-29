---
name: adr
description: Challenge and record the project's decisions while designing — a business rule, boundary, ownership, integration or technology choice being made or revisited, or a proposal that may contradict an earlier decision. Checks against .about/adr/, surfaces implicit decisions, probes alternatives and cost, and writes an ADR when a decision is hard to reverse, not obvious without an explanation, and a real trade-off. Not for merely reading ADRs for context.
---

# ADR

You are shaping the project's decisions, not just writing them down. Make each one explicit
and justified; don't just agree.

## Files

`.about/adr/<subject>.md` at the git repo's root — one subject per file, its decisions as they
stand now ([format](format.md)). Read the existing titles and drafts before you start; create
the folder with the first ADR. The project's own conventions (numbered files, another path, an
ADR template or skill) win.

## Check

Before accepting a proposal, look for an ADR it contradicts and call it out: "ADR ordering says
Ordering talks to Billing by events — this adds a direct call. Follow it, or change it?"
Never contradict an accepted ADR silently.

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
is a finding — don't paper over it: record it in a `proposed` ADR if the decision is worth one,
otherwise raise it as an open question. Ask a few pointed questions at a time, not a
questionnaire.

## Record

Write an ADR only when all three hold — otherwise the conversation is the record:
1. **Hard to reverse** — changing course later is costly.
2. **Not obvious without an explanation** — someone who wasn't in the discussion would ask
   "why this way?" or take it for a mistake and "fix" it.
3. **A real trade-off** — genuine alternatives existed and one won for stated reasons.

- A decision goes into the ADR on its subject, a new file only for a new subject. Decided → no
  Status line. Still open → a `Status: proposed` ADR of its own with the options, a draft to
  edit freely; once settled, rewrite it as the decision taken ("we won't do X" is a decision
  too) and merge it into the ADR on its subject, or drop its Status line.
- An ADR says what holds now. When a decision changes, edit it in place and update the Date;
  git keeps the earlier text. The choice it drops moves to Considered options, marked
  `(until <date>)` with why, so nobody proposes it again unwarned.
- Tell the user in one line what changed.
