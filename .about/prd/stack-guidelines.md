# louie's stack Guidelines hold only rules that are current and that change what Claude writes

## Problem

louie's Guidelines for a stack were written in 2026-10 and never measured rule by rule: `go.md`
still advised `chi`, which the go-vue template's ADR stack rejects for the standard `ServeMux`,
and knew no `uuid` package, which Go 1.27 ships; and on 2026-11-22 the default model and Claude
Sonnet followed every rule of `typescript.md` that an eval checked without louie at all. Every
session that touches a stack pays for the whole file (ADR guidelines), so a stale rule misleads
Claude and a redundant one costs context for nothing.

## Users

- Everyone in a project with louie on who has Claude write Go, TypeScript, Vue or Tailwind, write
  tests, or update dependencies.
- Not for: a project with its own documented conventions, which win over a Guideline as before.

## Success signal

- Each rule in `go.md`, `typescript.md`, `vue.md`, `tailwind.md`, `testing.md` and
  `dependencies.md` has a grader, in a case in `evals/<guideline>/`, that fails without louie in at
  least one run on the default model (Claude Opus on 2026-11-22) or Claude Sonnet and passes with
  it in every run on both, 3 runs an arm (ADR evals); a rule with no such grader is not in the
  file. On 2026-11-22, before this work, none of the six had a case.
- No rule is wrong for the current release on the day of its file's pass: Go 1.27, TypeScript 7,
  Node 24, Vue 3.5, Tailwind 4. A rule for a feature newer than a project may run names the
  release it came in, as `uuid` does Go 1.27.

## Scope

- Each of the six files, one at a time, each its own commit:
  1. An eval case per file in `evals/<guideline>/`, written before any text it tests (ADR
     evals), its graders one per rule, a regex over the file Claude writes where one can tell the
     rule's breach, run 3 times an arm with louie and without, on the default model and on Claude
     Sonnet. A grader that fails only because another rule's grader did (a route not wired at
     all fails "routed by method" too) measures that other rule, and is dropped.
  2. Every rule is checked against the current release's own docs or release notes; a rule a
     release made wrong or obsolete is rewritten or removed.
  3. A rule whose grader passes without louie in every run on both models is removed; one that
     fails without and passes with is kept; a new rule comes only with a grader that fails without
     louie and passes with it.
  A rule no regex can tell from the file Claude writes (a flag cleared in `finally`, a component
  that only renders, a major rolled back with its reason) gets a judge grader, `type: llm`, which
  counts toward the score only once its verdicts match a hand count of the first 3 runs. One case
  whose grader checks the rule as worded is enough to remove it.
- A first pass for two, on 2026-11-22; their rules with no grader yet get one, or leave:
  - `go.md`: UUIDs from Go 1.27's `uuid` package added, as no run took it without louie; `chi`
    removed, which no run took even with louie, and the standard `testing` package and got/want
    messages, which both models wrote unasked (`evals/go/api`).
  - `typescript.md`: no `any`, `unknown` at the edge, no `enum`, no class, the `node:` prefix and
    `import type` removed, as both models kept all six unasked; the script on `bun` removed too,
    as both ran a script on Node unasked, its `.ts` imports and all. Neither case stays.
- `dependencies.md` gains, with no case, a cooldown on a release too fresh to trust (pnpm's
  `minimumReleaseAge`, npm's `min-release-age`) and an audit before the report (`npm audit`,
  `govulncheck`): they need a registry, which the eval's sandbox has no network for, and ADR evals
  records the exception.
- ADR guidelines' measured rules follow the files: `typescript`'s "no `any`" leaves its list, as
  the rule left the file.
- A case that passes without louie on both models is deleted, and ADR evals records it as dropped,
  as for its earlier cases.

## Non-goals

- `principles`, `design`, `debugging`, `ci` and `writing-for-agents`: rules for any project, some
  already with cases (`evals/principles`, `evals/design`).
- `python.md`, measured by its own PRD (PRD python).
- New stacks (`react`, `rust`, `sql`), which wait in the Inbox.
- How and when a Guideline reaches Claude: its signals, the index and the 10,000-character limit
  stay as ADR guidelines has them.
- Vue 3.6 and Vapor mode, still a release candidate on 2026-11-22.

## Anti-goals

- A rule removed because one case passed without louie, where another kind of task would have
  broken it: a grader checks the rule as it reads, not one example of it.
- A rule that contradicts a project's documented conventions or the go-vue template's ADRs: the
  template is louie's own, and a Guideline that argues with it is a failure.
- A Guideline that grows: each file is no longer after its pass than before, but for a rule a
  failing case added.

## Acceptance criteria

- `evals/go/api`: in a Go 1.27 module with no dependencies, Claude, asked to add a create and a
  get endpoint with a generated UUID id, wires the routes in `cmd/api/main.go`, imports the `uuid`
  package and logs with a `…Context` variant of `slog`; each of the three graders fails without
  louie in at least one run on one of the two models and passes with it in every run on both, 3
  runs an arm.
- Every bullet left in each of the six files, `go.md`'s and `typescript.md`'s among them, has a
  grader in a case in `evals/<guideline>/` scored as above, but `dependencies.md`'s cooldown and
  audit.
- In `plugins/louie/guidelines/`, ``grep -nE '`(chi|bun|any|enum)`' go.md typescript.md`` finds
  nothing.
- Each of the six files, after its pass, has no more characters than before it but for the rules a
  failing grader added, each with its grader named in its commit.
- `mise run check` passes.
