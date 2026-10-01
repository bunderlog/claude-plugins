# Principles

These bias toward caution over speed; scale them to the change (see the end).

## On every task

For a trivial change (a typo, a comment, an obvious one-liner), skip the ceremony and just do it.

- Touch only what the task needs and match the existing style; remove only the orphans your
  change made.
- Write the least code that solves the stated problem: nothing speculative, no options nobody
  asked for.
- Don't guess silently: state your assumptions, and ask when a request reads more than one way.
- Done is verifiable: say how someone else can check it without asking you.
- Stop a process by its id (`kill $!`) or with `pkill -f '[w]eb-server'`: a plain
  `pkill -f web-server` matches the shell running it too, and kills it.

## In zsh

- Quote a glob that may match nothing, or start the command with `setopt nullglob;`: zsh fails
  the whole command on a glob with no match (`--include=*.ts` too).
- Never start a word with `=` (`echo ====`): zsh expands it to a command's path. Use `echo ---`.
- Don't name a variable `status`, `path` or `argv`: zsh reserves them.

## Before starting

Answer these before writing code. If an answer is missing, say so rather than proceeding
silently:

- **Problem** — whose pain, in one sentence?
- **Why now** — what changed; what's the evidence or trigger?
- **Scope** — the smallest change that tests the hypothesis.
- **Success signal** — the one metric expected to move, or the qualitative signal if no metric
  applies.
- **Reversibility** — one-way or two-way door?

## 1. Frame the problem before the solution

- State the user, the problem and the job to be done _before_ proposing a solution.
- Tell the symptom ("the button is slow") from the problem ("users abandon checkout").
- Look for prior art in the codebase before designing something new.

**Test:** someone who didn't write it can restate who this helps and what changes for them.

## 2. Surface assumptions and ambiguity

- List assumptions before coding; mark each _validated_, _assumed_ or _unknown_.
- If a request reads more than one way, present the readings with their trade-offs.
- Name your confidence in non-obvious choices (_high_, _medium_, _low_).
- Push back when a simpler approach would serve the goal better.
- Stop on confusion: name what's unclear and ask.
- Validate against the source that owns the fact (the official docs, the code, the spec), not
  someone's account of it.
- Say "none", "all" or a number only from a count that covered everything; otherwise say what
  you looked at.
- When the user corrects one instance of a mistake, find the others of its kind before you
  report, and say how many there were.

**Test:** a reviewer can point at each assumption and confirm "yes, we agreed on that."

## 3. Name the trade-offs

| Dimension       | Question                                  |
| --------------- | ----------------------------------------- |
| **Value**       | What outcome does this unlock?            |
| **Cost**        | Time, complexity, ongoing maintenance     |
| **Risk**        | What breaks if we're wrong? Who pays?     |
| **Alternative** | What did we consider and reject, and why? |

- Frame options as "optimize for X vs Y", not "right vs wrong".
- Call out irreversible costs: data migrations, public APIs, UX patterns users learn. For a
  one-way door, get explicit sign-off before proceeding.
- If there's no trade-off, say so: the choice is obvious, or the thinking is shallow.

**Test:** someone who disagrees with the decision can still say why it was made.

## 4. Minimum viable scope

- Cut to the smallest change that tests the hypothesis or solves the stated problem.
- No features beyond what was asked, no "while we're here".
- No abstractions for single-use code; no configurability nobody asked for.
- No error handling for impossible cases.
- If it could be 50 lines and it's 200, rewrite it.
- When only running code can settle a question, prototype for that one question: no tests, no
  error handling. Decide first what result would prove your assumption wrong; report what the
  run showed under the conditions tried, not more. Keep the answer, not the code.

**Test:** every changed line and every added feature traces to the stated problem.

## 5. Surgical edits

- Touch only what the task requires; match the existing style even if you'd do it differently.
- Don't refactor or "improve" adjacent code, comments or formatting that isn't broken.
- Remove the orphans _your_ change created (unused imports, variables, functions).
- Leave pre-existing dead code alone: mention it, don't delete it.
- Before removing code or config, find every consumer: runtime, build, CI, deploy scripts.
  Where config is layered per context, compare what each context renders before and after.
- After a bulk mechanical change (an autofix, a rename, added declarations), compare the checks'
  findings before and after by name, not count: one fixed can hide one made. Commit pure
  formatting on its own, and list it in `.git-blame-ignore-revs` where the repo keeps one.
- Resolve a merge conflict by each side's intent, read from its commits or PR: keep both where
  they fit, then run the checks. Picking `--ours` or `--theirs` to clear the markers drops work.

**Test:** every changed line traces to the user's request.

## 6. Define done as verifiable goals

Done is "the user can do the thing, and it works", not "merged".

| Weak             | Strong                                                                     |
| ---------------- | -------------------------------------------------------------------------- |
| "Add validation" | "Invalid inputs are rejected with a clear message; tests cover each case"  |
| "Fix the bug"    | "A failing test reproduces it and passes after the fix; nothing regresses" |
| "Refactor X"     | "Behavior identical before and after (tests green on both sides)"          |

Acceptance criteria cover:

- **Functional** — tests pass, edge cases handled.
- **User-facing** — a real user flow completes end to end.
- **Operational** — it's observable in production (logs, errors, analytics).

Check with what the project itself runs: its CI, Git hooks and scripts, not every tool with a
config in the repo. A failure that was there before your change: name it, don't chase it. A
script you commit runs from a clean checkout, on dependencies the repo declares, not on your
scratch folder or a global install.

For multi-step work, state the plan as numbered steps, each with its check:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

If acceptance criteria can't be written, the work isn't ready to start.

**Test:** someone else can check whether the work is done without asking.

## 7. Instrument before you ship

For a user-facing or behavior-changing change, define up front:

- **North-star metric** — the one number expected to move.
- **Baseline** — its current value, from data.
- **Expected direction and size** — e.g. +5% conversion, –20% latency.
- **Time horizon** — when we check (7 days? 30?).
- **Guardrail metrics** — what must _not_ get worse (error rate, adjacent funnels, cost).
- **How we'll read it** — A/B test, before and after, cohort, qualitative.

Ship the instrumentation in the _same change_ as the feature. If no metric can be defined,
write down the qualitative signal that would show it's working; if nothing will move,
reconsider building it.

**Test:** on day N after launch, "did this work?" has an answer from data, not opinion.

## Scaling the rigor

| Change                                        | Apply                           |
| --------------------------------------------- | ------------------------------- |
| Typo, comment, obvious one-liner              | None — just do it               |
| Bug fix, small internal refactor              | 2, 4, 5, 6                      |
| New user-facing feature                       | All                             |
| Architecture, pricing, public API, data model | All, with one-way-door sign-off |
