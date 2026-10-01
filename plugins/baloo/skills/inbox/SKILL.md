---
name: inbox
description: Go through the project's Inbox, .about/inbox.md, with the user — when they ask to go through, triage or clear the inbox, or what is still open. Drops the items the code, the ADRs, the glossary or the Guidelines already settle, ranks the rest, asks a few at a time what to do with each (decide now, fix now, file an issue, keep, drop) with a recommended answer, and applies the answers. Not for adding a single item.
---

# Inbox

Go through `.about/inbox.md` at the git repo's root with the user. Each item is a `## <title>`,
a line `<YYYY-MM-DD> · <source>`, then what it is and what would settle it. What to do with an
item is the user's call; finding out whether something already settles it is your job.

## 1. Drop what is settled

Read every item, then what it names: the code, the ADRs in `.about/adr/`, `.about/glossary.md`
and the project's Guidelines. Delete each item they already settle, naming what settled it.

## 2. Rank

Rank the rest by what waiting costs: a bug before a finding, a finding before a decision still
open, and a decision others depend on before one nothing waits for.

## 3. Ask

A few items at a time, most costly first, ask what to do with each, with the AskUserQuestion
tool: each question says the item in a line; the options are the ones below that fit it, your
recommendation first, marked "(Recommended)".

- **Decide now**: settle it here, with the `adr` skill for a decision or `glossary` for a term.
- **Fix now**: it becomes this session's work, after the triage.
- **File an issue**: write it as an Issue, with the `issue` skill; the item goes once it is filed.
- **Keep**: it stays as it is, or with what you learned added.
- **Drop**: it is not worth doing.

## 4. Apply

After each round, delete the items decided, filed or dropped, and edit the ones kept. End with
one line per item: what happened to it, and what is left in the inbox. Don't commit.
