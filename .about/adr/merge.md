# `/louie:merge`'s push rests on the implementer's instructions, its merge on louie's `code-host` server, the Code host holding main

Date: 2026-11-27

A Workflow's script runs no git of its own, so what a `louie:implementer` stage did is only what
it reports. The force-push stage's rules (only with `--force-with-lease`, only to the pull
request's branch, never the default branch) stay text in `plugins/louie/agents/implementer.md`,
which the script's prompt backs by naming the exact lease: the script checks the sha the push
reports. The merge's rules are in the code of louie's MCP server `code-host`, whose `pr_merge` the
implementer is told to call (ADR code-host): it merges only when the pull request's head is the
commit the last Verification passed and the default branch's tip is still the rebase's base, and
deletes no branch; on GitHub `gh pr merge --match-head-commit` checks the head, on Bitbucket Cloud
it is read again right before the merge. As before, nothing stops a stage running another
command, and the script takes `base-moved` on the merge stage's word.

What holds the default branch is the code host: in this repo a ruleset on it (`main: no
force-push or deletion`, since 2026-11-21) refuses a force-push and a deletion, while the plain
pushes of `mise run release` still go through. A project using louie protects its own default
branch the same way; louie doesn't set it up.

A merge onto a base that moved in the seconds between `pr_merge` reading the tip and merging is
accepted, and on Bitbucket Cloud one whose head moved in those seconds too: the default branch's CI runs after every merge and catches a combination that
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
