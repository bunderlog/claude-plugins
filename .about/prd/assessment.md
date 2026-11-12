# bagheera keeps counting how useful each part of bunderlog is and how well it works

## Problem

Whether a part of bunderlog stays (a Check, a skill, a Guideline, a Workflow, session start's
context) is decided from one-off measurements: the last, of three weeks up to 2026-10-07, ran on
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
rather than a measurement made by hand.

## Scope

- **Usefulness**: a part is used, and what it gives is taken: a Proposal accepted, a Check's denial
  real, an ADR or PRD read before an edit to what it names.
- **Quality**: what a part does when used is right: a Check's denials mostly real, a skill's eval
  better with the plugin than without.
- At each session's end, bagheera counts that session from its Transcript, read only through
  `condense` (ADR transcripts), which gains the events the count needs: each Read and Edit with
  its path, in order; each skill loaded, by name; what followed a Check's denial; and the length of
  each plugin's session start text, told apart by its first line. The count runs in a process of
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
  - the characters each plugin's session start put in the context.
- A report command, over every repo on the machine or one named, over the last 30 days by default
  or a number of days given, with the window before it beside each figure:
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
- PRD delivery's and PRD batch's signals: a Workflow runs in the background and its result reaches
  the session's Transcript as a task-notification once it ends, so a later change of this PRD can
  count them from there (seen on 2026-11-12, the first louie Workflow run on this machine).

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
