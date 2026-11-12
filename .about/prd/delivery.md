# louie takes an agreed Issue to a pull request checked against what the project agreed

## Problem

A developer takes each agreed Issue to a pull request by hand, steering Claude step by step, and
the check of a change against the project's ADRs, glossary and criteria seldom runs: `verify` ran
in none of about 200 sessions until Claude offered it (ADR verify). The one project that automated
the way, `webui`, keeps its pipeline in its own `.claude/workflows/`, where no other project can
use it and it has already drifted from the rest (PRD harness).

## Users

- A developer in a project with louie on and Workflows turned on, who has an Issue with acceptance
  criteria and wants a pull request without steering each step.
- Not for: work with no agreed criteria (an exploration, a design still open), which goes to the
  `interview` or `prd` skill first.

## Success signal

Within a month of the Release of `deliver`, an Issue goes from `/louie:plan` through
`/louie:deliver` to an opened pull request in at least two projects besides `webui`, and every
such pull request carries the Verification's verdict on each acceptance criterion.

## Scope

- Three Workflows in `plugins/louie/workflows/`, built in this order, a Release each: `verify`,
  `plan`, `deliver`. Their stages run as louie's agents in `agents/` (`louie:verifier`,
  `louie:planner`, `louie:implementer`), each given the Guidelines' index by the `SubagentStart`
  Hook. Each stage takes what the person agreed from the Issue and `.about/`, not from the
  session's conversation.
- An Issue is a page in the tracker the project's `CLAUDE.md` or `AGENTS.md` names, read through
  its command-line client or connector, or `.about/issues/<slug>.md` (ADR issues). Its slug is the
  tracker's key (`KAZ-123`, `issue-42` for GitHub's `#42`) or the file's name.
- `/louie:verify` takes what the `verify` skill takes (a commit range, a branch, a pull request, an
  Issue or a PRD; by default the current branch's commits since the default branch plus the
  working tree) and runs four verifiers at once, one per source of what was agreed: the ADRs, the
  glossary, the Guidelines that fit the repo, and the criteria of the Issue or PRD the change
  serves. Each returns its departures, each with `file:line` and whether it blocks, and the
  criteria-verifier a verdict per criterion: met and tested, met with no test, not met, or
  couldn't check by reading. The script joins them into one report. It changes nothing. It replaces
  the `verify` skill; where the session has no Workflow tool, Claude offers the `louie:verifier`
  agent by name instead.
- `/louie:plan <Issue>` reads the Issue, what in `.about/` it touches and the code, and returns a
  plan: what changes where and which criterion each change serves, its confidence, the decisions
  only the person can make, and "nothing to build" with the commit that already meets the criteria.
  It changes nothing. The person settles the open decisions, and the session writes them into the
  Issue or an ADR, committed and pushed before `deliver`.
- `/louie:deliver <Issue>`, one agent per stage unless said, stages 1 and 2 one agent:
  1. stops `blocked:` before changing anything when the repo has no remote, the tracker's client
     is missing, or the local default branch or `.about/` holds what the remote's lacks;
  2. fetches and adds a worktree under `.claude/worktrees/<slug>` on a new branch from the
     remote's default branch, `<slug>`, then `<slug>-2` and on when taken, never reusing,
     deleting or rewriting an earlier one, and leaving the person's checkout as it was; the
     worktree stays after the run, and every later stage works in it;
  3. plans again, stopping when the Issue has no acceptance criteria, leaves a decision open, or
     has nothing to build, and then discarding the worktree and branch it made, which hold
     nothing; a question outside the Issue's criteria is not a decision for the person, nor is a
     way to build the planner recommends that no criterion, ADR or the Issue rules out: it is an
     assumption the plan builds on;
  4. implements in commits in the project's format, with the checks the project's `CLAUDE.md` or
     README names (`mise run check`, `make verify`) passing on the last one, or stops
     `blocked:checks` with their output; a change that delivers an Issue kept in
     `.about/issues/` deletes its file, as ADR issues has it;
  5. verifies with `verify`'s four verifiers, against where the branch started: it fails on a
     criterion not met or a blocking departure;
  6. on a failure, implements again with the findings and verifies again, at most three rounds,
     ending `failed:rework-budget` after the third, and `failed:not-converging` sooner when a
     round fails on the same criteria and departures as the one before;
  7. pushes the branch and opens a pull request to the default branch, its body each criterion with
     its verdict, the plan's assumptions for the person to review, and the Verification's report;
     a draft when a criterion is met with no test or couldn't be checked, or a departure doesn't
     block.
  It returns how the run ended: `done:pr-opened`, `done:draft-pr`, `done:nothing-to-build`,
  `blocked:<why>` or `failed:<why>`, with the reason. That is at most 23 agents (1 + 1 + 1 + 4 +
  3 × 5 + 1), so Claude Code's `Large workflow` warning, past 25, never shows, and a project sets
  no `workflowSizeGuideline`, which only advises Claude on a script it writes itself.
- A permission prompt in a stage pauses the run until the person answers, as for any Workflow; the
  README names the commands to allow for a run with none.
- Setting a project up turns Workflows on, `enableWorkflows: true` in its `.claude/settings.json`
  (PRD project-setup).
- The Workflows are JavaScript, since Claude Code runs them; `node` is needed only by this repo's
  tests and CI, which run each script with its agents stubbed, and no user installs it for louie.
- With the Release of each Workflow, the ADRs it changes are rewritten: verify (a Verification by
  four agents, run by a Workflow, and also as a stage of a run the person started, without asking
  again), issues (a run from an Issue to a pull request, which `ship` was declined for, since each
  repo's flow is its own: the project's checks command, commit format and tracker come from what
  it names), plugin (JavaScript for Workflows) and the glossary (Verification, Workflow).

## Non-goals

- Several Issues in one run: PRD batch.
- Running the app to test the change: the project's own test or Claude Code's `/verify`; the pull
  request says the app was not run.
- Fixing a red CI run after the pull request: a session with the `ci` Guideline, or Claude Code's
  own fixing of a pull request's CI.
- Merging the pull request, closing an Issue in a tracker, or writing an Issue: the person's, and
  the `issue` skill's.
- Removing old worktrees and branches: the person's.
- Templates and `upgrade-all`: PRD templates.

## Anti-goals

- A pull request opened ready to merge whose Verification failed, or a run that ends without
  saying why.
- `deliver` changing the person's checkout, their current branch or the default branch.
- `plan` or `verify` changing a file, a branch or the tracker.

## Acceptance criteria

- Each Workflow's `meta` is a plain literal with `name`, `description` and the `phases` its
  `phase()` calls use, and no script calls `Date.now()`, `Math.random()` or `import()`.
  → test: tests/louie/test_workflows.py "test_meta_and_body"
- In a project with louie and Workflows on, `/louie:plan`, `/louie:deliver` and `/louie:verify`
  are offered as commands; with louie off, none is. Checked by hand at each of their Releases.
- `/louie:verify` on a branch that breaks an ADR's rule and leaves one PRD criterion unmet reports
  both, each with `file:line` and its source, and `git status` and the branches are the same before
  and after. The report: → test: tests/workflows/verify.test.mjs "verify fails on an ADR departure
  and an unmet criterion"; the run, checked by hand at its Release.
- `/louie:plan` on an Issue whose criteria a commit on the default branch already meets returns
  "nothing to build" naming that commit, and leaves the repo's branches and files as they were.
- `/louie:deliver` on an Issue with acceptance criteria, in a repo with a remote, ends
  `done:pr-opened`: the pull request targets the default branch from a new branch, its commits pass
  the project's Git hooks, its body lists each criterion with a verdict, and the person's checkout
  has the branch and files it had before.
- With an earlier run's branch `<slug>` present, `/louie:deliver` works on `<slug>-2` and leaves
  `<slug>` as it was.
- With its agents stubbed, `deliver` ends `failed:rework-budget` when every Verification fails on
  new criteria, after three reworks, and `failed:not-converging` when two in a row fail on the same
  ones, and opens no pull request in either; it schedules at most 23 agents in any case.
  → test: tests/workflows/deliver.test.mjs "deliver ends failed:rework-budget after three reworks,
  with at most 23 agents", "deliver ends failed:not-converging when two rounds fail on the same"
- With its agents stubbed, a Verification that passes with a criterion met but not tested opens the
  pull request as a draft, the criterion's verdict in its body.
  → test: tests/workflows/deliver.test.mjs "deliver opens a draft when a criterion is met with no
  test"
- With its agents stubbed, the pull request's body lists the plan's assumptions.
  → test: tests/workflows/deliver.test.mjs "deliver lists the plan's assumptions in the pull
  request's body, for the person to review"
- In a repo with no remote, with the tracker's client missing, or with a local commit on the default
  branch the remote lacks, `deliver` ends `blocked:` with the reason and no branch, worktree or
  commit made. The script's part: → test: tests/workflows/deliver.test.mjs "deliver stops before
  changing anything when prepare stops, or the plan isn't ready"; the prepare stage's, by hand.
- In a session with no Workflow tool, Claude offers the `louie:verifier` agent by name at the end
  of a task that serves an Issue or a PRD, instead of `/louie:verify` (ADR verify's offer).

## Open questions

None. Built first: whether a Workflow's `agentType` takes a plugin's agent (`louie:verifier`);
where it doesn't, each stage's prompt carries its agent's instructions, and the `SubagentStart`
Hook's index goes into the prompt too.
