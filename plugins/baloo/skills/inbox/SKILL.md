---
name: inbox
description: Go through the project's Inbox, .about/inbox.md, with the user — when they ask to go through, triage or clear the inbox, or what is still open, or the Session review's proposals for it. Settles those proposals first, then ranks the items, then a few at a time drops those the code, the ADRs, the glossary or the Guidelines already settle and asks what to do with the rest (decide now, fix now, file an issue, keep, drop) with a recommended answer, applying each round's answers so the user can stop and pick up later where they left off. Not for adding a single item.
---

# Inbox

Go through `.about/inbox.md` at the git repo's root with the user. Each item is a `## <title>`,
a line `<YYYY-MM-DD> · <source>`, then what it is and what would settle it; an item the user went
through once and kept ends its date line in `· kept <YYYY-MM-DD>`. What to do with an item is the
user's call; finding out whether something already settles it is your job. The file goes with its
last item.

The user can stop after any round and come back later: each round's answers are applied before
the next, and the next run starts from what nobody has gone through yet.

## 1. Proposals

Session reviews propose changes to the Inbox, which wait in `.about/proposals/<review>.md` for the
user. From the project folder, run
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' proposals`:
it lists those still waiting, a line each, `<review> <id> <target> <kind> <path>: <title>`. Take
the ones whose target is `inbox`, read each in its file, and ask, with the AskUserQuestion tool,
accept, reject or defer, your recommendation first: reject for one marked stale, and no defer for
one deferred twice. Apply each accepted one by its edit as written; where what you applied
differs from its After, add to the Proposal an `Applied:` block of the text you applied, fenced as
After is, and log it `accepted-edited`. Log each answer with
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' review-decision <review> <id> accepted|accepted-edited|rejected|deferred`.
An item an accepted one adds is one nobody has gone through yet.

## 2. Rank

Read every item's text, not yet what it names. Rank those not kept by what waiting costs: a bug
before a finding, a finding before a decision still open, and a decision others depend on before
one nothing waits for. The kept ones come after all of them, the oldest mark first; sooner only
when the user asks, or what their item says would settle it has happened.

## 3. Round

Take the next few. For each, read what it names: the code, the ADRs in `.about/adr/`,
`.about/glossary.md` and the project's Guidelines. Delete each item they already settle, naming
what settled it.

Ask what to do with the rest, with the AskUserQuestion tool: each question says the item in a
line; the options are the ones below that fit it, your recommendation first, marked
"(Recommended)".

- **Decide now**: settle it here, with the `adr` skill for a decision or `glossary` for a term.
- **Fix now**: it becomes this session's work, after the triage.
- **File an issue**: write it as an Issue, with the `issue` skill.
- **Keep**: it stays, with what you learned added, and its date line ends in `· kept <today>`,
  replacing an older mark.
- **Drop**: it is not worth doing.

## 4. Apply

After each round, delete the items decided, filed or dropped, and edit the ones kept. Then go on
with the next round, until the user stops or nothing is left to go through. End with one line per
item gone through: what happened to it; then how many items are left, and how many of them
nobody has gone through yet. Don't commit.
