# Review each round of implement for bugs, and check the pushed head before the pull request

2026-11-18

## Symptom

The goal: `/louie:implement` catches bugs before a person reads the change, and what reaches the
pull request is what was checked. Now nothing in a run looks for bugs, since the verifiers check
only what the project agreed (ADR verify), and nothing checks that the branch the pull request
stage pushed ends at the commit the last Verification passed. PRD implement, as changed on
2026-11-18, has both.

## Evidence

- `plugins/louie/workflows/implement.js`, `build()`: each round runs `louie:verify` alone, and
  reworks up to `MAX_REWORK = 3`; the pull request stage's answer (`PR_SCHEMA`) carries no commit,
  so the script can't tell what it pushed.
- `plugins/louie/agents/verifier.md`: "Not for hunting bugs, which a code review does".
- `tests/workflows/implement.test.mjs`: "implement ends failed:rework-budget after three reworks,
  with at most 23 agents".

## Acceptance criteria

PRD implement's, as changed on 2026-11-18:
- step 5 and 6 of `/louie:implement`: `louie:reviewer` beside the four verifiers each round, a bug
  reworked, at most two reworks, `failed:not-converging` on the same criteria, departures and bugs;
- step 7: the review's findings that aren't bugs in the pull request's body, and
  `blocked:pull-request` when the pushed branch doesn't end at the commit the last Verification
  passed;
- the criteria "at most 21 agents", "a round whose review finds a bug reworks", and "a pull
  request stage after which the pushed branch ends at another commit", each with its test in
  `tests/workflows/implement.test.mjs`.

## Comments

### 2026-11-18 · fix option

`louie:reviewer` in `plugins/louie/agents/reviewer.md`, with `tools: Read, Grep, Glob, Bash` like
the verifier, answering a schema of findings, each `at` (`file:line`), what is wrong, and `bug`
true or false; `build()` runs it with `parallel()` beside `workflow('louie:verify')` on the same
commits, and a round fails on a bug as on a Verification's failure. `PR_SCHEMA` gains `head`, the
commit the pushed branch ends at, which the script compares with the last commit of the last
round's implement or rework stage.

### 2026-11-18 · docs

ADR plugin names louie's agents; README names the verifier. Each gets the reviewer where it
lists them, and ADR verify a line that the reviewer is not a verifier: it looks for bugs, not for
what the project agreed.
