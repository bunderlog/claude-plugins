---
name: tidy
description: Recheck the project's files for consistency, duplicates and wordiness, and fix what is clear — when asked to tidy up or recheck docs, skills, prompts or config, or after a series of edits to them. Not for hunting bugs in code.
---

# Tidy

Read the files as a set: most problems sit between files, not inside one.

## Scope

Every tracked or new text file, unless the user names a subset. Read each in full, not in
excerpts. Read the project's glossary and ADRs (e.g. `.about/`) first: they are the reference,
not something to reopen.

## Check

- **Consistency.** One thing, one name, everywhere — the glossary's word if there is one. Facts
  that must match do: commands, paths, names, versions, descriptions repeated in manifests.
  Nothing points to a file, section or option that no longer exists.
- **Duplicates.** A fact stated twice will drift. Keep one source; link or import it elsewhere.
  Keep a repeat only when the copies can't reach each other (units loaded separately, such as
  skills) or serve different readers — and say so.
- **Wordiness.** Cut what doesn't change meaning or behaviour; merge points that overlap; one
  example per point.
- **Mechanics.** Run the project's own checks (validators, linters, line length, trailing
  spaces) — see its CLAUDE.md or README.

## Fix and report

- Fix what is clearly wrong right away, then re-read the changed lines: a fix can break a line
  wrap, a link or a term.
- For a judgement call, give a recommendation and ask.
- Don't reopen recorded decisions; don't commit.
- Report in three short lists: fixed, needs a decision, kept on purpose (and why). If nothing is
  left, say so plainly.
