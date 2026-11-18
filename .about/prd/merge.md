# louie merges louie's pull requests one at a time, each rebased and checked again first

## Problem

A developer runs `/louie:implement` on one Ticket per session, so the overlap check of PRD batch,
which compares only the plans of one run, never fires. Ten Tickets sharing files give ten pull
requests built from the same default branch: merged one by one, the later ones conflict, and two
changes that touch different lines of one file merge with no conflict yet duplicate or contradict
each other. The developer resolves each conflict by hand, and the result is merged with no
Verification or review after it, though `implement` checked only the commits before the rebase.
Even with no conflict, merging is steered by hand: on 2026-11-18, bunderlog/web#1 took three
prompts (mark it ready, wait for CI and merge, remove the branch).

## Users

- A developer in a project with louie and Workflows on, with pull requests `/louie:implement`
  opened, who has read them and wants them on the default branch without steering each merge.
- Not for: a pull request the person hasn't reviewed. Naming it to `/louie:merge` is the person's
  consent to merge it, as a pull request's Assumptions are theirs to review (glossary Assumption).

## Success signal

In the month after its Release, on the maintainer's machine, no pull request `/louie:implement`
opened reaches the default branch through a conflict the person resolved by hand, and the default
branch's CI passes after every merge `/louie:merge` makes.

## Scope

- `/louie:merge <PR> <PR> …`: a Workflow in `plugins/louie/workflows/` that takes one to five pull
  requests of the current repo, each its number, `#number` or URL, as one text split on whitespace
  or as `{ prs: [...] }`. Each is counted by its number, so `42`, `#42` and its URL are one pull
  request; a URL of another repo ends `blocked:other-repo`. On one pull request it returns as on
  several.
- Before any agent runs it ends `blocked:no-pr` on none and `blocked:too-many` on more than five.
- It takes the pull requests strictly one at a time, in the order named: every stage of one,
  the first included, starts only once the one before has merged or stopped.
- Each stage is a `louie:implementer` stage of its own, but the Verification's and the review's.
  For each pull request:
  1. **prepare** stops, changing nothing, when the pull request is closed or merged
     (`blocked:closed`), a draft (`blocked:draft`), doesn't target the default branch
     (`blocked:not-default`), or its Ticket can't be found (`blocked:no-ticket`); or when the
     merge method can't be told (`blocked:merge-method`). The Ticket is the one the pull
     request's body names (`implement` writes `Delivers <Ticket>.`), else the branch's name, read
     from the default branch, where a Ticket in `.about/tickets/` stays until the pull request
     that delivers it merges. The merge method is the one the project's `CLAUDE.md`, `AGENTS.md`
     or an ADR names (`gh pr merge --rebase` in this repo, ADR releases), else the only one the
     code host allows; two sources that name different ones, or a host that allows several with
     none named, can't be told. Otherwise it records the pull request's head commit and adds a
     worktree under `.claude/worktrees/` at that commit, detached, so the branch's own worktree
     from `implement` and the person's checkout stay as they were.
  2. **rebase** rebases onto the remote's default branch as it is now and:
     - resolves each conflict where both sides' intents can be kept;
     - reads the commits the default branch gained since the pull request's base, and removes from
       the pull request a change one of them already makes (a second link to the same page);
     - stops `blocked:needs-decision` where keeping one Ticket's intent drops another's, with or
       without a textual conflict, naming the files, the options and the one it recommends;
     - runs the project's checks until they pass on the last commit, as stage 4 of PRD implement
       does, or stops `blocked:checks` with their output.
  3. **verify** runs the Verification against the Ticket and `louie:reviewer` on the commits since
     the default branch, on every pull request, whether the rebase had a conflict or not. A
     failure goes to a **rework**, given the Ticket and the findings, with at most two reworks and
     the endings of stages 5 and 6 of PRD implement (`failed:rework-budget`,
     `failed:not-converging`).
  4. **push** pushes to the pull request's branch with `--force-with-lease=<branch>:<sha>`, the
     head commit prepare recorded, ending `blocked:push` when the remote branch moved since; the
     script then checks the pushed branch ends at the commit the last Verification passed, ending
     `blocked:push-mismatch` when it doesn't.
  5. **ci** waits, for an hour at most, for the pull request's checks on the code host: every
     check it reports, a skipped or neutral one counting as passed, none at all as nothing to wait
     for. A failing check ends `blocked:ci` with its name and link; still running after the hour,
     `blocked:ci-timeout`.
  6. **merge** merges by the method from prepare, only when the pull request's head is still the
     commit the last Verification passed and its base is still the default branch's tip, ending
     `blocked:base-moved` when the default branch moved since the rebase (someone else merged),
     `blocked:merge` with the code host's message when the merge is refused, and `done:merged`.
- A pull request that stops leaves the others to go on: the next is rebased onto the default
  branch as it is then, without the one that stopped.
- It returns `results`, each pull request with how its run ended and the reason; `decisions`, each
  `needs-decision` under its pull request with its options and the one recommended; a `report` of
  both as text; and a `verdict`: `done:all`, `done:some` or `blocked:none`, or `blocked:no-pr` or
  `blocked:too-many` before any agent runs. A decision stays in the report: the person settles it
  and runs the pull request again; it goes to no Inbox, since the pull request can't merge until it
  is settled (ADR inbox).
- At most 22 agents per pull request (prepare 1, rebase 1, Verification 4 and review 1, two
  reworks of 1 + 4 + 1, push 1, ci 1, merge 1), as PRD implement has; a run on more than one can
  pass 25, so Claude Code's `Large workflow` warning shows for it, as for PRD batch's.
- louie's Guidelines give the run's result with its tokens, agents and minutes, as for every louie
  Workflow (PRD implement).
- At its Release:
  - ADR tickets says louie merges a pull request only through `/louie:merge`, on the person naming
    it, while `implement` still never does, and its `ship` option says why merging became a
    Workflow of its own: the merge method and checks come from what the project names;
  - PRD implement's non-goal on merging points here;
  - the glossary names the Workflow, its Verification is one a `merge` run makes too, and its Open
    decision is one a rebase finds too;
  - `louie:implementer` and `louie:reviewer` run through `/louie:merge` as well as `implement`, and
    the implementer may push a pull request's branch with a lease and merge it, never the
    default branch itself.

## Non-goals

- Pull requests not opened by `/louie:implement`, or with no Ticket: the Verification needs the
  Ticket's criteria.
- Merging a draft: a draft waits for the person (PRD implement).
- Fixing a red CI run: a session with the `ci` Guideline (PRD ci).
- Rebasing again when the default branch moves between the rebase and the merge: the person runs
  the pull request again.
- Ordering the pull requests by what depends on what: the order is the person's.
- Removing the merged branch and its worktrees, or closing a Ticket in a tracker: the person's, as
  in PRD implement.
- Pull requests in another repo, or more than five at once.

## Anti-goals

- A pull request merged whose last Verification, review, project checks or CI failed, or whose
  head at the merge isn't the commit they passed.
- A change dropped, from either side of a conflict or a duplicate, where it kept one Ticket's
  intent over another's without the person choosing.
- The person's checkout, current branch or local default branch changed, or a branch force-pushed
  over commits the run didn't read.
- One pull request's stop ending the others' runs, or a run that ends without saying, for each,
  why.

## Acceptance criteria

- With its agents stubbed, a run on three pull requests starts the second's prepare only after the
  first has merged, and the third's only after the second has merged or stopped.
  → test: tests/workflows/merge.test.mjs "merge takes the pull requests one at a time, each starting
  once the one before has merged or stopped"
- With its agents stubbed, a run on three pull requests where the second's rebase needs an Open
  decision merges the first and the third, returns the second as `blocked:needs-decision` with its
  files, options and recommended option in `decisions`, runs no push stage for it, and ends
  `done:some`.
  → test: tests/workflows/merge.test.mjs "merge goes on with the others when a rebase needs an Open
  decision, and reports it under its pull request"
- With its agents stubbed, a pull request whose rebase reports no conflict still runs the four
  verifiers and the review before its push.
  → test: tests/workflows/merge.test.mjs "merge verifies and reviews a pull request whose rebase had
  no conflict before its push"
- With its agents stubbed, a rebase that reports `blocked:checks` runs no Verification, push or
  merge for that pull request.
  → test: tests/workflows/merge.test.mjs "merge runs no Verification, push or merge after a rebase
  whose checks fail"
- With its agents stubbed, a pull request whose Verification fails on new criteria every round
  ends `failed:rework-budget` after two reworks, and runs no push or merge stage.
  → test: tests/workflows/merge.test.mjs "merge ends failed:rework-budget after two reworks when
  every Verification fails on new criteria"
- With its agents stubbed, a push after which the branch ends at another commit than the one the
  last Verification passed ends `blocked:push-mismatch`, and a ci stage reporting a failing check
  ends `blocked:ci` naming it, with no merge stage run in either.
  → test: tests/workflows/merge.test.mjs "merge merges nothing when the pushed branch isn't the
  commit the Verification passed, or a check fails"
- With its agents stubbed, a prepare reporting a draft, a closed pull request, a missing Ticket or
  a merge method it can't tell ends `blocked:draft`, `blocked:closed`, `blocked:no-ticket` or
  `blocked:merge-method`, and runs no rebase stage.
  → test: tests/workflows/merge.test.mjs "merge stops a pull request at prepare when it is a draft,
  closed, not on the default branch, in another repo, or has no Ticket or no merge method it can
  tell"
- With its agents stubbed, six distinct pull requests end `blocked:too-many` and no pull request
  `blocked:no-pr`, each scheduling no agent; `42 #42` and the URL of pull request 42 run it once.
  → test: tests/workflows/merge.test.mjs "merge takes one to five pull requests, each counted once
  by its number"
- With its agents stubbed, a run on N pull requests schedules at most 22 agents per pull request.
  → test: tests/workflows/merge.test.mjs "merge schedules at most 22 agents a pull request"
- In a repo with a remote, two pull requests from `/louie:implement` that both add a link to the
  same file's list merge in the order named: the second is rebased onto the first, keeps both
  links, or drops its own when it is the same link, is verified, and is merged by the project's
  method after its CI passes; the person's checkout has the branch and files it had before.
  Checked by hand at its Release.
- In a repo with a remote, a pull request whose branch someone pushed to after prepare read it
  ends `blocked:push`, and the remote branch keeps that commit. Checked by hand at its Release.

## Open questions

- None. Settled 2026-11-18: drafts are skipped; a stopped pull request doesn't stop the others;
  the merge waits for the code host's checks; the Workflow is `/louie:merge`; the rebase stage
  looks for duplicates and contradictions with what merged since, not only textual conflicts.
