# louie plans several Issues first, then delivers those that are ready and don't overlap

Status: proposed

## Problem

A developer with several agreed Issues starts `/louie:deliver` on each, and the runs stop one by
one, each on a decision its plan found only then: Issues louie-new-scaffold and louie-new-api each
stopped mid-way on a choice the earlier `/louie:plan` hadn't raised (Inbox, "`deliver` re-plans and
stops on a decision the earlier plan didn't raise"). Runs started side by side can also change the
same files, and their pull requests then conflict on the default branch.

## Users

- A developer in a project with louie and Workflows on, who has two or more Issues with acceptance
  criteria and wants a pull request for each without answering decisions one run at a time.
- Not for: one Issue, which `/louie:deliver` takes; Issues one of which needs another merged first,
  which go one at a time.

## Success signal

In the runs of `/louie:batch` in the month after its Release, no Issue stops on a decision after
its implementation started: every decision for the person comes in the run's one report, before
any commit; and no two pull requests of one run conflict on the default branch.

## Scope

- `/louie:batch <Issue> <Issue> …`, a Workflow in `plugins/louie/workflows/`. It takes the Issues
  as one text split on whitespace, or as `{ issues: [...] }`, each as `/louie:deliver` takes it (a
  tracker's key or URL, or a file in `.about/issues/`). The same text twice counts once; from one
  to five Issues after that.
- First each Issue is prepared, one after another, as `deliver`'s stages 1 and 2 do (PRD
  delivery): a worktree and branch of its own. Then all are planned at once. No Issue is
  implemented until every plan is in.
- An Issue goes on only when its plan is ready. One whose plan stops (a decision for the person,
  no acceptance criteria, low confidence, nothing to build, a tool failing) ends as its plan does,
  with the worktree and branch it made discarded.
- Of the ready Issues, taken in the order the person named them, one whose plan changes a file an
  earlier Issue that goes on also changes ends `blocked:overlaps`, naming that Issue and the files,
  its worktree and branch discarded; the person runs it again once that pull request is merged.
  An Issue blocked this way blocks no later one. Two plans change the same file when the `where`
  of a change in each is the same path, or one is a folder holding the other.
- Each Issue left is delivered by `deliver`'s stages 4 to 7 from the plan the batch made, without
  planning again, all at once: `batch` runs `deliver` with that Issue's worktree, branch and plan,
  so neither script copies the other. One Issue's run ending `blocked:` or `failed:` doesn't stop
  the others.
- It returns `results`, each Issue with how its run ended, as `deliver` names it, its branch, and
  its pull request's URL or the reason; `decisions`, every decision any plan raised for the person,
  under its Issue, with the options and the one recommended; a `report` of both as text; and a
  `verdict`: `done:all` when every Issue ended `done:`, `done:some` when some did, `blocked:none`
  when none did, or `blocked:no-issue` or `blocked:too-many` before any agent runs.
- At most 23 agents per Issue, as `deliver` has, and one more for each discarded worktree. A run
  on more than one Issue can pass 25, so Claude Code's `Large workflow` warning shows for it.
- At its Release, ADR issues names `batch` beside `deliver`, and the Inbox item on `deliver`
  re-planning says what `batch` settles of it.

## Non-goals

- Stacked pull requests, an overlapping Issue branched from an earlier one's branch: it waits for
  that pull request's merge instead.
- Ordering Issues by what depends on what, beyond the files their plans change.
- Answering a plan's decisions or writing them into the Issue: the person's, before running the
  Issue again.
- The person handing `/louie:deliver` a plan already made: the Inbox item stays for that.
- Rerunning an Issue that ended `failed:` or `blocked:`, Issues in another repo, or more than five
  at once.

## Anti-goals

- An Issue implemented before every plan of its run is in.
- Two pull requests from one run whose plans named the same file.
- One Issue's failure ending the others' runs, or a run that ends without saying, for each Issue,
  why.
- The person's checkout, current branch or default branch changed.

## Acceptance criteria

- With its agents stubbed, a run on three Issues schedules no implement stage before all three
  plan stages return, and no two prepare stages at once.
- With its agents stubbed, a run on three Issues of which one plan needs a decision opens pull
  requests for the other two, and returns the third as `blocked:needs-decision`, its decisions with
  their options in `decisions`, and its worktree discarded; the run's verdict is `done:some`.
- With its agents stubbed, a run on Issues A, B and C, where A's and B's plans change `src/a.go`
  and B's and C's change `src/b/`, opens pull requests for A and C, and returns B as
  `blocked:overlaps` naming A and `src/a.go`, its worktree discarded.
- With its agents stubbed, plans changing `web/` and `web/app.ts` overlap; `web/app.ts` and
  `web/app.tsx` don't.
- With its agents stubbed, a run on two Issues where the first's implementation fails the
  project's checks returns the first as `blocked:checks` and opens the second's pull request.
- With its agents stubbed, no planner runs after the plan stages, whatever the Verifications
  find.
- With its agents stubbed, a run on six distinct Issues ends `blocked:too-many`, and one on none
  `blocked:no-issue`, each scheduling no agent; six names of which two are the same text run five
  Issues.
- With its agents stubbed, a run on N Issues schedules at most 23 agents per Issue, plus one per
  discarded worktree.
- `/louie:batch` on two independent Issues, in a repo with a remote, opens two pull requests to
  the default branch, each from its own new branch, and the person's checkout has the branch and
  files it had before. Checked by hand at its Release.

## Open questions

None. Built first: whether a Workflow runs inside a Workflow that itself runs inside a Workflow
(`batch` → `deliver` → `verify`); where it doesn't, `batch` runs `deliver`'s stages itself.
