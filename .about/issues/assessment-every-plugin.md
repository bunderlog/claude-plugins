# The Assessment counts hathi, louie's Guidelines and Workflows, and reports by plugin

2026-11-16

## Symptom

`/bagheera:assess` reports under the heading "bagheera assessment", and an answer read from it
covers bagheera's parts alone. It counts nothing of `hathi`'s Git hooks, of louie's Guidelines or
of louie's Workflows, so whether to keep a part of louie or a Check of `hathi`'s is still decided
by counting by hand. PRD assessment, agreed on 2026-11-16, asks for bagheera to count every
part of bunderlog, baloo's, louie's, its own and `hathi`'s, and for the report to be grouped by
plugin.

## Evidence

- `bagheera assess` of 0.64.1 on this machine: its first line is `bagheera assessment: the last 30
  days…`; no `hathi` figure, no Guideline figure, no Workflow figure.
- The Transcripts on this machine hold 74 lines `…; run: hathi explain <check>` in 14 sessions
  (`conventional-commits` 30, `no-stale-adr-date` 28, `no-secrets-in-commits` 10,
  `no-ai-coauthor` 4), none counted.
- louie's Hook gives a Guideline as added context `The <name> Guideline applies to …`
  (`plugins/louie/scripts/louie/guidelines.py:488`), which the Transcript keeps as a PostToolUse
  attachment; `condense` doesn't read it.
- `plugins/bagheera/scripts/bagheera/assess.py`: `_count` records denials, skills, index and
  session start only; `report` prints them ungrouped.

## Acceptance criteria

PRD assessment's criteria, all of which must pass, and of them the five this Issue adds:
- the Git hook's failure of `conventional-commits`, fixed and nothing, and `hathi check` by hand;
- `typescript` "1 of 2", `debugging` in one session, the index alone counting none;
- the `verify` Workflow completed and `plan` with no end;
- the report's figures under baloo, louie, bagheera and `hathi`, its first line naming bunderlog;
- the two records of the Release before, the new figures covering 1 session.

## Comments

### 2026-11-16 · cause

The Assessment was built with louie's Workflows as a Non-goal and `hathi`'s and the Guidelines'
figures left to a later change (ADR measurement: "the rest still by hand"); the report's heading
took the plugin's name.

### 2026-11-16 · fix option

`condense.facts` gains the three events (a Guideline given or read, a `git commit`/`git push`
and whether it printed a `hathi explain` line, a Workflow call with its task's notification);
`_count` adds the fields; `report` groups by plugin. Records without the new fields are recounted
the way `backfill` counts, once, by a mark per figure. Risk: `condense` is shared with the Retro
and the Session review (ADR transcripts); new events must not change what those read.

### 2026-11-16 · decision

`hathi`'s failures count the commits and pushes of a Workflow's agents too (their Transcripts under
`subagents/workflows/`), each agent's failures fixed only by a later pass in that agent's own
Transcript: louie's `deliver` commits from its agents, where `hathi` runs as well.
