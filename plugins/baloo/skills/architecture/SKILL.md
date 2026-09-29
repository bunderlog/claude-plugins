---
name: architecture
description: Review the code's architecture for deepenings — shallow modules, pass-throughs, modules that always change together, code hard to test through its interface — when the user asks for an architecture review, where to refactor, or why an area is hard to change or test. Scans the recently changed hot spots, ranks candidates against the project's ADRs, and works the chosen one into a plan agreed with the user. Not for designing a new module from scratch or reviewing a diff.
---

# Architecture

Find where fewer, deeper modules would make the code easier to change and test, and agree on
one change with the user. You propose; change code only when the user asks.

A **module** is anything with an interface: a function, a class, a package, a service. Its
**interface** is all a caller must know to use it: the types, and also the order of calls, the
errors, the limits and the config. A **seam** is where that interface sits: the public boundary
callers and tests go through. A module is **shallow** when its interface is nearly as big as
the code behind it. A **deepening** puts more behaviour behind fewer, smaller interfaces.

Read the project's glossary and ADRs (e.g. `.about/`) first. Name modules after the glossary's
terms ("the Order intake module", not "OrderHandler").

## 1. Scope

If the user named an area, a module or a pain, look only there. Otherwise find the hot spots,
the files that change most, and which of them change in the same commits:

```sh
git log --since=6.months --name-only --format=%h
```

Deepening pays off where code keeps changing; widen the net only when the history shows no hot
spot. Done when you have named the areas to read, and why each.

## 2. Scan

Read each area with its callers and tests; hand a large one to a subagent with the signs below,
asking for `file:line` evidence. Signs:

- Understanding one concept means reading many small modules.
- A shallow module, such as a pass-through.
- Modules that change in the same commits.
- The same logic repeated in each caller of one module.
- Logic split into small pure functions to test it, while the bugs sit in how they're called.
- An interface in front of a dependency with only one implementation, counting a test fake.
- A test that reaches past the interface: private state, a fake of the project's own module.
- Code with no tests, or hard to test through its interface.

Apply the deletion test to each suspect: picture the code without it. If nothing gets harder,
fold it into its callers or neighbours; if every caller would grow the same logic, it earns its
place. Done when each area has its signs with evidence, or "none found".

## 3. Report

For each candidate:

- **Modules** — the files involved.
- **Friction** — what it costs now, with evidence (`file:line`, commits).
- **Deepening** — in plain words, what moves behind which interface; no interface design yet.
- **Gain** — what callers no longer need to know, where changes and bugs would concentrate,
  which tests move to the new interface and which go.
- **Cost** — the callers and tests to change; anything that can't change cheaply (a public
  API, stored data).
- **Strength** — Strong, Worth exploring or Speculative.

Drop a candidate an accepted ADR rules out, unless the friction is real enough to reopen it:
then name the ADR and why. Rank by gain against cost; end with the one you'd do first and why,
and ask which to explore. If nothing is worth its cost, say so plainly.

## 4. Work the chosen one

- Probe it with the user, a few pointed questions at a time: constraints, callers and
  dependencies, what sits behind the seam, which tests survive. Look facts up yourself; put
  only decisions to the user.
- Design the interface twice: sketch two or three radically different ones (the smallest; the
  one that makes the common call trivial; one with an interface before each varying dependency),
  each with a usage example and what it hides. Compare what each hides and where its seam sits,
  and recommend one, or a hybrid.
- Propose a glossary term for a deepened module that has none. When the user rejects a
  candidate for a reason that will hold ("that API is public"), offer to record it as an ADR so
  the next review doesn't propose it again; not for "not now".

Done when the user agrees on a plan: the interface, the tests to move or delete, and steps
that each leave the tests green. Don't commit.
