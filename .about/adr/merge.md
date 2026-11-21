# `/louie:merge`'s push and merge rest on the implementer's instructions, the code host holding main

Date: 2026-11-21

A Workflow's script runs no git of its own, so what a `louie:implementer` stage did is only what
it reports. The force-push stage's rules (only with `--force-with-lease`, only to the pull
request's branch, never the default branch) and the merge stage's check that the default branch's
tip is still the rebase's base stay text in `plugins/louie/agents/implementer.md`, which the
script's prompt backs by naming the exact lease and base: the script checks the sha the push
reports, as it does now, and takes `base-moved` on the merge stage's word.

What holds the default branch is the code host: in this repo a ruleset on it (`main: no
force-push or deletion`, since 2026-11-21) refuses a force-push and a deletion, while the plain
pushes of `mise run release` still go through. A project using louie protects its own default
branch the same way; louie doesn't set it up.

A merge onto a base that moved in the seconds between the stage's `git ls-remote` and `gh pr
merge` is accepted: the default branch's CI runs after every merge and catches a combination that
breaks, and the merge can be reverted (PRD merge's non-goal of rebasing again stands).

## Considered options

- A Check that denies `git push --force` without a lease or to the default branch — holds it in
  every session, but is a new always-on Check (ADR checks) for a push the prompt already spells
  out, and the code host refuses the one that would cost most.
- The code host requiring a pull request's branch to be up to date before a merge — needs
  required status checks, and this repo's CI path filters leave some pull requests with none, so
  they could never merge.
- Text alone, the default branch unprotected — a force-push to main, the one push the lease
  doesn't limit, would then rest on the agent obeying.

## Consequences

- A force-push to a pull request's branch without the lease, or to another branch than the
  default one, isn't caught; the lease the prompt names limits what it can overwrite.
- Revisit when a run force-pushes without the lease or to a branch it wasn't given, or merges onto
  a moved base that CI then fails on.
