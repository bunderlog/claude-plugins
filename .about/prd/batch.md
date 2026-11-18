# louie plans several Tickets first, then implements those that are ready and don't overlap

## Problem

A developer with several agreed Tickets starts `/louie:implement` on each, and the runs stop one by
one, each on a decision its plan found only then: Tickets louie-new-scaffold and louie-new-api each
stopped mid-way on a choice the earlier `/louie:plan` hadn't raised. Runs started side by side can
also change the same files, and their pull requests then conflict on the default branch.

## Users

- A developer in a project with louie and Workflows on, who has two or more Tickets with acceptance
  criteria and wants a pull request for each without answering decisions one run at a time.
- Not for: Tickets one of which needs another merged first, which go one at a time.

## Success signal

In the runs of `/louie:implement` on several Tickets in the month after its Release, no Ticket stops
on a decision after its implementation started: every Open decision comes in the run's one
report, before any commit; and no two pull requests of one run conflict on the default branch.

## Scope

- `/louie:implement <Ticket> <Ticket> …`: the `implement` Workflow takes several Tickets, as one text
  split on whitespace or as `{ tickets: [...] }`, each as it takes one (a tracker's key or URL, or a
  file in `.about/tickets/`). The same text twice counts once; from one to five Tickets after that.
  On one Ticket it runs and returns as PRD implement has it. Claude Code runs a Workflow inside a
  Workflow one level deep only, so `implement`, which runs `plan` and `verify` as stages, can't be a
  stage of another: the Tickets are its own.
- First each Ticket is prepared, one after another, as stages 1 and 2 of PRD implement do: a
  worktree and branch of its own. Then all are planned at once. No Ticket is implemented until
  every plan is in.
- A Ticket goes on only when its plan is ready. One whose plan stops (an Open decision, no
  acceptance criteria, low confidence, nothing to build, a tool failing) ends as its plan does,
  with the worktree and branch it made discarded.
- Of the ready Tickets, taken in the order the person named them, one whose plan changes a file an
  earlier Ticket that goes on also changes ends `blocked:overlaps`, naming that Ticket and the files,
  its worktree and branch discarded; the person runs it again once that pull request is merged.
  A Ticket blocked this way blocks no later one. Two plans change the same file when the `where`
  of a change in each is the same path, or one is a folder holding the other.
- Each Ticket left goes through stages 4 to 7 of PRD implement from the plan this run made, without
  planning again, all at once. One Ticket's run ending `blocked:` or `failed:` doesn't stop the
  others.
- It returns `results`, each Ticket with how its run ended, as PRD implement names it, its branch,
  and its pull request's URL or the reason; `decisions`, every decision any plan raised for the
  person, under its Ticket, with the options and the one recommended; a `report` of both as text;
  and a `verdict`: `done:all` when every Ticket ended `done:`, `done:some` when some did,
  `blocked:none` when none did, or `blocked:no-ticket` or `blocked:too-many` before any agent runs.
- At most 23 agents per Ticket, as PRD implement has, and one more for each discarded worktree. A
  run on more than one Ticket can pass 25, so Claude Code's `Large workflow` warning shows for it.
- At its Release, ADR tickets says `implement` takes several Tickets.

## Non-goals

- Stacked pull requests, an overlapping Ticket branched from an earlier one's branch: it waits for
  that pull request's merge instead.
- Ordering Tickets by what depends on what, beyond the files their plans change.
- Answering a plan's decisions or writing them into the Ticket: the person's, before running the
  Ticket again.
- The person handing `/louie:implement` a plan already made: declined on 2026-11-12, as a way to
  build the planner recommends is now an assumption the plan builds on (PRD implement).
- Rerunning a Ticket that ended `failed:` or `blocked:`, Tickets in another repo, or more than five
  at once.

## Anti-goals

- A Ticket implemented before every plan of its run is in.
- Two pull requests from one run whose plans named the same file.
- One Ticket's failure ending the others' runs, or a run that ends without saying, for each Ticket,
  why.
- The person's checkout, current branch or default branch changed.

## Acceptance criteria

- With its agents stubbed, a run on three Tickets schedules no implement stage before all three
  plan stages return, and no two prepare stages at once.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets prepares them one at a time
  and plans them all before building any"
- With its agents stubbed, a run on three Tickets of which one plan needs a decision opens pull
  requests for the other two, and returns the third as `blocked:needs-decision`, its decisions with
  their options in `decisions`, and its worktree discarded; the run's verdict is `done:some`.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets implements the ready ones and
  lists the decisions of the rest"
- With its agents stubbed, a run on Tickets A, B and C, where A's and B's plans change `src/a.go`
  and B's and C's change `src/b/`, opens pull requests for A and C, and returns B as
  `blocked:overlaps` naming A and `src/a.go`, its worktree discarded.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets holds back one whose plan
  changes a file an earlier one does"
- With its agents stubbed, plans changing `web/` and `web/app.ts` overlap; `web/app.ts` and
  `web/app.tsx` don't.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets takes a folder and a file in
  it as one, and two files as two"
- With its agents stubbed, a run on two Tickets where the first's implementation fails the
  project's checks returns the first as `blocked:checks` and opens the second's pull request.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets goes on with the others when
  one fails the checks"
- With its agents stubbed, no planner runs after the plan stages, whatever the Verifications
  find; and a run on N Tickets schedules at most 23 agents per Ticket, plus one per discarded
  worktree.
  → test: tests/workflows/implement.test.mjs "implement on several Tickets plans each once, with at
  most 23 agents a Ticket"
- With its agents stubbed, a run on six distinct Tickets ends `blocked:too-many`, and one on none
  `blocked:no-ticket`, each scheduling no agent; six names of which two are the same text run five
  Tickets.
  → test: tests/workflows/implement.test.mjs "implement takes at most five Tickets, and a Ticket named
  twice once"
- `/louie:implement` on two independent Tickets, in a repo with a remote, opens two pull requests to
  the default branch, each from its own new branch, and the person's checkout has the branch and
  files it had before. Checked by hand at its Release.
