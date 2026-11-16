# bagheera keeps counting how useful each part of bunderlog is and how well it works

## Problem

Whether a part of bunderlog stays (a Check, a skill, a Guideline, a Workflow, session start's
context, a Check of `hathi`'s) is decided from one-off measurements: the last, of three weeks up to 2026-10-07, ran on
scripts kept outside this repo (ADR measurement), and the Transcripts it read are deleted by
Claude Code after 30 days. No PRD's success signal that sessions could answer is counted without
writing a script by hand, and the eval suites run only when someone remembers (ADR evals). So the
maintainer learns that a part stopped paying off, or got worse, only when a session stumbles on it.

## Users

- bunderlog's maintainer, deciding what to keep, change or drop, from the sessions on their own
  machines.
- Not for: anyone else's sessions. Nothing leaves the machine it was counted on.

## Success signal

The success signals that sessions and bagheera's data folder can answer, PRD index's and PRD
session-review's, and PRD visibility's longest wait of a Proposal, go from counted by hand to
answered by one command, and the next decision to keep or drop a part cites that command's report
rather than a measurement made by hand. Each of baloo, louie, bagheera and `hathi` has its own
figures in it, so that decision can be about a part of any of them.

## Scope

- **Usefulness**: a part is used, and what it gives is taken: a Proposal accepted, a Check's denial
  real, an ADR or PRD read before an edit to what it names.
- **Quality**: what a part does when used is right: a Check's denials mostly real, a skill's eval
  better with the plugin than without.
- bagheera alone counts, for every part of bunderlog: baloo's, louie's, its own and `hathi`'s,
  from the Transcript; the other plugins and `hathi` add nothing for it.
- At each session's end, bagheera counts that session from its Transcript, read only through
  `condense` (ADR transcripts), which gains the events the count needs: each Read and Edit with
  its path, in order; each skill loaded, by name; what followed a Check's denial; the length of
  each plugin's session start text, told apart by its first line; each Guideline louie's Hook
  gave; each commit or push a Git hook running `hathi` stopped, and the commits and pushes after
  it; and each of louie's Workflows run, with its task-notification. The count runs in a process of
  its own the SessionEnd Hook starts detached, which reads the Transcript itself.
- It appends one record to bagheera's data folder: the session's id and date, the repo as the
  Session review's log names it (its origin's URL, or its root), the repo's root and the
  Transcript's path on this machine, bagheera's version, and counts per part. A record holds names,
  paths and numbers, never the session's text. Records are kept until the person deletes them.
- What a record counts:
  - each Check's denials, by its `bagheera:<check>:` prefix or `baloo:<check>:` before 0.41.0,
    and what followed each in its turn: a later call that worked on what the denial named
    (another way), other calls (went on), or none (nothing), close to ADR measurement's reading;
  - each of bunderlog's skills loaded;
  - the edits to a file an ADR or PRD names, and of those, the ones it was read before, as PRD
    index counts them;
  - the characters each plugin's session start put in the context;
  - each Check of `hathi`'s that stopped a `git commit` or `git push`, by the line it prints
    (`<check>: …; run: hathi explain <check>`), and what followed in the session: fixed, a later
    command of the same kind (a commit for a commit, a push for a push) that passed, which fixes
    every failure of that kind before it; or nothing (ADR measurement). A pass with a flag that
    skips the Git hooks can't follow, as `no-git-hook-bypass` denies it and counts that denial. A
    `hathi check` run by hand is no Git hook's failure. The commits and pushes of the agents of a
    Workflow the session ran count as the session's, each agent's in its own order;
  - each Guideline in the context: given by louie's Hook, whose added context names it (`The
    <name> Guideline applies to …`), or a Read of its file in louie's `guidelines/`; session
    start's index and the rules of `principles` it prints whole in every session are not counted.
    For a Guideline a Read of its file kind gives or Claude reads (ADR guidelines: `go` for `.go`,
    `typescript`, `vue`, `writing-for-agents`), whether it was in the context before the session's
    first edit of such a file; `testing` and `dependencies` come after their first edit by design,
    so for them and the rest only the sessions they came in;
  - each of louie's Workflows run (`plan`, `deliver`, `verify`), a Workflow tool call running one,
    and how it ended as the task-notification of that run's task says (completed, failed,
    stopped), or no end where none reached the Transcript. Its skill loaded counts as a skill
    besides. And what the run cost, from its agents' Transcripts: each agent's tokens (input,
    output, cache written and cache read) by model, and those at the model's prices in dollars,
    by the agent's type and its phase, never its prompt or label; the report gives each
    Workflow's runs' mean and total cost, and the phase that cost most.
- The first report after a Release that adds a figure counts again each record without it whose
  Transcript is still on disk, appending a new record for it; once the Transcript is gone, the
  record is left out of that figure, and the figure says how many sessions it covers.
- A report command, over every repo on the machine or one named, over the last 30 days by default
  or a number of days given, with the window before it beside each figure, headed for bunderlog
  and grouped by whose part it is: first the sessions counted, then baloo (its skills, PRD index,
  its session start), louie (its skills, Guidelines, Workflows, its session start), bagheera (its
  skills, the Checks' denials and those to label, the Session review, the Proposals waiting, its
  session start), `hathi` (its Git hooks' failures); a stale eval suite under its skill's plugin,
  and a session start of no plugin's in the first group:
  - per part, the sessions it was used in and its outcomes;
  - PRD index's and PRD session-review's signals as those PRDs state them;
  - the Session review's Proposals accepted, rejected and deferred, from its log; and from each
    repo's `.about/proposals/` and the runs log, the Inbox items proposed and the longest a
    Proposal has waited (PRD visibility);
  - where the repo has `evals/`, each suite whose skill's text changed in a commit after the suite's
    latest result in `evals/results/`, with that result.
- A Check's denial is labeled real or false by the maintainer, named by its session and tool call:
  the report lists the unlabeled ones, each with its call as `condense` masks it, while its
  Transcript still exists, and a command stores the label. One whose Transcript is gone unlabeled
  counts as unlabeled.
- The first report also counts the sessions whose Transcripts are still on disk from before the
  feature.

## Non-goals

- Counting anyone else's sessions, or sending a count anywhere.
- Running the eval suites: they stay run by hand (ADR evals); the report only says which are stale.
- A model judging denials or sessions.
- Showing anything in the Status line or at session start: the report is asked for.
- Turning a part off from the report.
- What a user is asked after a week of use (PRD status-line, PRD visibility): no session shows it.
- PRD delivery's and PRD batch's own success signals: the report counts the Workflows' runs and
  ends, not what came of their pull requests.
- `hathi`'s runs outside a session: a commit made in a terminal, and CI. Only what a session's
  Transcript shows is counted.

## Anti-goals

- A session's code, prompts or a Secret reach the records.
- Ending a session gets slower.
- Figures nobody decides by: each names the PRD or ADR it decides for.

## Acceptance criteria

- A session in a repo with bagheera on, whose prompts and tool output hold `AKIAIOSFODNN7EXAMPLE`
  and the word `zebra-umbrella`, ends: one record is appended to bagheera's data folder, holding
  neither string nor any prompt's text.
  → test: tests/bagheera/test_assess.py "test_a_record_holds_no_text_of_the_session"
- The SessionEnd Hook reads the Transcript once, as before the feature, and counts nothing itself:
  with a 50 MB Transcript, the record appears once the detached process ends, and the Hook's run
  time differs from the release before by less than a tenth.
- A headless session, a Session review's own session, and a session outside a repo add no record.
  → test: tests/bagheera/test_assess.py
  "test_no_count_in_a_headless_session_a_session_review_or_outside_a_repo"
- Of a session with three edits to files an ADR names, two after a Read of that ADR, the report
  counts "2 of 3" for PRD index.
  → test: tests/bagheera/test_assess.py
  "test_index_counts_edits_after_a_read_of_the_adr_naming_them"
- A denial by `no-secrets-in-context` followed by the same file read through another command, and
  one followed by nothing, are counted "another-way" and "nothing"; one prefixed
  `baloo:no-secrets-in-context:` counts for the same Check.
  → test: tests/bagheera/test_assess.py "test_what_followed_a_denial"
- Labeled with the label command, a denial counts in its Check's real or false share in the next
  report; a denial whose Transcript was deleted before it was labeled counts as unlabeled.
  → test: tests/bagheera/test_assess.py "test_labels_count_and_a_deleted_transcript_stays_unlabeled"
- After its Transcripts are deleted, a session's record still counts in a report over 90 days.
  → test: tests/bagheera/test_assess.py "test_a_record_outlives_its_transcript"
- With `plugins/baloo/skills/adr/SKILL.md` changed in a commit after the latest result of
  `evals/adr/`, the report run in this repo names `adr` with that result; run in a repo without
  `evals/`, it says nothing of evals.
  → test: tests/bagheera/test_assess.py "test_stale_eval_suites_only_where_the_repo_has_evals"
- A Proposal written to a repo's `.about/proposals/` 10 days ago and not decided shows as waiting
  10 days, under that repo.
  → test: tests/bagheera/test_assess.py "test_a_proposal_waiting_ten_days"
- Each figure in the report names the PRD or ADR it decides for.
  → test: tests/bagheera/test_assess.py "test_each_figure_names_what_it_decides_for"
- A session's `git commit` printing `conventional-commits: …; run: hathi explain
  conventional-commits`, then a commit that passed, counts one failure of `conventional-commits`,
  fixed; one with no commit after it counts one failure, nothing; a failed commit followed only by
  a push that passed counts nothing; a `hathi check commit-msg` run in Bash counts no failure.
- Of two sessions each editing a `.ts` file, one where louie's Hook gave `typescript` after a Read
  before that edit and one with no Read before it, the report counts `typescript` "1 of 2"; a
  session where the Hook gave `debugging` counts it in one session; session start's index alone
  counts no Guideline.
- A session that ran louie's `verify` Workflow, whose task-notification says it completed, and one
  that ran `plan` with no task-notification, count `verify` 1 run, completed 1, and `plan` 1 run,
  no end 1.
- A run of louie's `plan` Workflow whose one agent, a `louie:planner` in the phase Plan, used
  1,000,000 tokens of input and 100,000 of output on one model counts as its cost those tokens at
  that model's prices, under `plan`, with Plan its costliest phase; a model with no price known
  counts its tokens and no dollars, and says so.
- The report's figures stand under baloo, louie, bagheera and `hathi`, in that order, each figure
  under the plugin whose part it counts, the Checks' denials under bagheera and the skills each
  under its own plugin; its first line names bunderlog.
- Of two records of the Release before, without the new figures, one whose Transcript is still on
  disk counts in the new figures of the next report, and one whose Transcript is gone counts in
  the old figures only: the new figures say they cover 1 session.
