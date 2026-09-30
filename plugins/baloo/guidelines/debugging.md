# Debugging

For a bug: behavior that differs from what the code, its docs or tests promise, or from what it
used to do, such as wrong output, a crash, a failing or flaky test, a slowdown. Find the cause
before you fix anything.

## 1. Build a feedback loop

- Before any hypothesis, build one command that goes red on this bug and green once it's fixed.
  Reading code to guess the cause first is the failure this step prevents.
- Try, roughly in order: a failing test; a request to a running server; a CLI call diffed
  against known-good output; a headless browser script; a captured request or log replayed
  through the code path; a throwaway harness calling the code directly; random inputs, many
  times over; `git bisect run` between a good and a bad commit; the same input through the old
  and new version, diffed.
- Make it fast (seconds), sharp (it asserts the user's exact symptom, not "didn't crash") and
  deterministic (pin time, seed randomness, isolate files and network). For a flaky bug, repeat
  it, run it in parallel or add load until it fails often enough to debug.
- If you can't build one, stop: list what you tried and ask for access to where it fails, a
  captured artifact (logs, a HAR, a dump) or permission to add temporary logging. Last resort:
  exact steps for the user to follow by hand, and what to paste back.

**Test:** you have run the loop and shown the command and its red output.

## 2. Shrink it

- Confirm it fails with the symptom the user described, not a nearby one.
- Remove inputs, config, callers and steps one at a time, re-running after each.

**Test:** every part left is needed for the loop to go red.

## 3. Rank hypotheses

- List 3–5, most likely first, each with a prediction: "If the cache key ignores the locale,
  clearing the cache makes it pass." One without a prediction is a guess: sharpen it or drop it.
- Show the list to the user, who may rule some out at once; don't wait if they're away.

**Test:** every hypothesis names what an experiment would show.

## 4. One experiment at a time

- One hypothesis, one change. Prefer a debugger or REPL; otherwise log only where the
  hypotheses differ, every line tagged with one prefix (`[DEBUG-a4f2]`) so cleanup is one grep.
- For a slowdown, measure a baseline and bisect; logs rarely show it.

**Test:** each hypothesis is confirmed or ruled out by an experiment you ran.

## 5. Lock the fix in

- Find the seam where a test hits the bug as it happens at the call site. Turn the shrunk loop
  into a failing test there, watch it fail, fix, watch it pass, then re-run the original loop.
- Where no seam reaches the bug, say that the design keeps it from being locked down, rather
  than write a shallow test that proves nothing.
- Remove the tagged lines and throwaway harnesses. Tell the user the causes and which
  hypotheses held, in a line or two; a commit message names the causes.

**Test:** the original loop is green, the regression test passes or the missing seam is
reported, and a grep for the tag finds nothing.
