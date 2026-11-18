# Add /louie:merge: merge louie's pull requests one at a time, each rebased and checked again

2026-11-18

## Symptom

The goal, as PRD merge has it: `/louie:merge <PR> …` takes pull requests `/louie:implement`
opened, one at a time in the order named, rebases each onto the default branch as it is then,
looks for duplicates and contradictions with what merged since, runs the project's checks, the
Verification and the review again, pushes, waits for the code host's CI and merges by the
project's method. Now louie stops at the pull request (ADR tickets: "It never merges"), so a
developer who runs `implement` one Ticket per session resolves the conflicts between its pull
requests by hand, and merges the result with no Verification after the rebase.

## Evidence

- `plugins/louie/workflows/`: `implement.js`, `plan.js`, `verify.js`; no Workflow merges.
- `plugins/louie/workflows/implement.js:245`: the pull request's body names its Ticket,
  `Delivers <Ticket>.`, which `merge` reads to find it.
- `plugins/louie/agents/implementer.md:3`: "Run only through /louie:implement"; `:12-13`: "Never
  touch the person's own checkout, its branches or the default branch"; `:27`: "never reuse,
  delete or rewrite an earlier one". `merge` force-pushes a pull request's branch with a lease and
  merges it through the code host.
- `plugins/louie/agents/reviewer.md:3`: "Run only through the /louie:implement Workflow".
- `.about/adr/tickets.md:29-30`: "It never merges and never closes a tracker's Ticket"; `:34`,
  the `ship` option declined.
- bunderlog/web#1, merged on 2026-11-18, took three prompts by hand: mark it ready, wait for CI
  and merge, remove the branch.

## Acceptance criteria

- Each of PRD merge's acceptance criteria (`.about/prd/merge.md`, "Acceptance criteria"), the
  stubbed ones each with its test in `tests/workflows/merge.test.mjs` linked from the PRD.
- PRD merge's Scope "At its Release" list done in the same change: ADR tickets, PRD implement's
  non-goal on merging, the glossary (Workflow, Verification, Open decision), and the descriptions
  and stages of `louie:implementer` and `louie:reviewer`.
- `tests/louie/test_workflows.py` "test_meta_and_body" passes with `merge.js` in
  `plugins/louie/workflows/`.

## Comments

### 2026-11-18 · fix option

`plugins/louie/workflows/merge.js`, built like `implement.js`: the script orders the stages and
every way out of them, `louie:implementer` gets new stages `merge-prepare`, `rebase`, `rework`
(reused, given the Ticket and the findings instead of a plan), `force-push`, `ci` and `merge`, and
the Verification runs as `workflow('louie:verify')` beside `louie:reviewer`, as in `build()`. The
loop over pull requests is a plain `for … await`, not `parallel()`, since each must start from the
default branch the one before left.
