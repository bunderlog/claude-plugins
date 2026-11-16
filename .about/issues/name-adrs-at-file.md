# louie names the ADRs and PRDs a file concerns when Claude first works on it

2026-11-16

## Symptom

Claude edits code without reading the ADR or PRD that the code rests on, even with session start's
index. In the index's first six days (0.52.0, 2026-11-10 to 2026-11-16), only 6 of 25 edits to a
file an ADR or PRD names came after a read of it, against PRD index's goal of more than half. When
a Hook gave each Guideline at its file instead of an index line, the Guidelines went from 5 of 79
to 15 of 22 (ADR guidelines). So louie's `PostToolUse` Hook is to name the ADRs and PRDs a file
concerns when Claude reads, edits or writes the file, as PRD index's Scope now says.

## Evidence

- `/bagheera:assess --days 6` on 2026-11-16: "PRD index: edits to a file an ADR or PRD names,
  after a read of it: 6 of 25 (2 of 17)".
- `plugins/louie/scripts/louie/cli.py`, `post_tool_use`: today it gives only Guidelines for a file
  (`guidelines.for_file`), once a session each, marked in `CLAUDE_PLUGIN_DATA/guidelines/shown/`.
- `plugins/bagheera/scripts/bagheera/assess.py`, `_PATH`, `_names` and `_index`: the rule for which
  file an ADR or PRD names, which PRD index says the Hook must share. The plugins share no code
  (ADR plugin), so louie keeps its own copy.

## Acceptance criteria

- Each of PRD index's acceptance criteria from "In a repo whose `.about/adr/a.md`" to "With
  `BALOO_SESSION_REVIEW` set, or in a repo with no `.about/`" passes, each linked to its test
  (`→ test: …`) in the PRD.
- On a list of ADR paths and repo files that bagheera's `assess._names` tests use, louie's copy of
  the rule gives the same answer for each, so the Hook fires exactly where the Assessment counts.
- ADR plugin's account of louie names this Hook, and that baloo stays a single `sh` Hook.
- In this repo, a Read of `plugins/louie/guidelines/go.md`, a file in the folder ADR guidelines
  names, names `.about/adr/guidelines.md`, the first time in a session.

## Comments

### 2026-11-16 · open point

How the Hook tells a subagent's call from the main thread's is unchecked. Claude Code's hook input
may carry `agent_id` and `agent_type` for a subagent's tool call; nothing in the plugins reads
them yet. Confirm that from a real Transcript or Claude Code's docs before building the subagent
criterion.

### 2026-11-16 · fix option

Mark what was named, and the ADRs and PRDs read, per session in `CLAUDE_PLUGIN_DATA`, beside the
Guidelines' `shown/` marks and forgotten after a week like them. Each Read of an `.about/adr/*.md`
or `.about/prd/*.md` file in the main thread marks that document read. Each Read, Edit or Write
of another file in the repo lists `.about/adr/` and `.about/prd/`, finds the paths in each, and
names those that match and aren't marked. That costs a read of about 40 small files per tool call
in this repo, and needs no cache to go stale.
