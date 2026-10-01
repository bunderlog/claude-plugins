# What is still to consider waits in `.about/inbox.md` until something settles it

Date: 2026-10-01

A decision or a term still open, and a bug or a finding left for later, had no common place: a
proposed ADR, the glossary's `## Unresolved`, or nowhere, and Claude's auto-memory took some,
where a teammate never sees them. In one real project a Hook of its own wrote about 18 todos in
12 of 246 runs, and fix commits later closed several; in another, the user asked four times in
nine minutes to move what auto-memory held into git, and about 16 memory files repeated the
repo's own `docs/issues/`.

So each is an item of the Inbox, `.about/inbox.md` at the repo's root (ADR about-folder): a
`## <title>`, a line `<YYYY-MM-DD> · <source>` naming who added it, then what it is and what would
settle it. The Session review adds what the conversation left open, or found and didn't fix (ADR
session-review); `adr` and `glossary` add what stays open, `retro` each fix the user didn't pick,
and a rule `principles` prints on every task sends anything else left for later there, a code
review's findings among them, rather than to Claude's memory. An item is deleted once the code,
an ADR, the glossary or the Guidelines settle it: by the change that settles it, or by the Session
review where the conversation did. Session start tells Claude how many items there are, one per
`## ` heading outside a code block, to tell the user, and that the `inbox` skill goes through them
with the user: it drops what is already settled, ranks the rest by what waiting costs, and asks
of each whether to decide it now, fix it now, file an Issue (ADR issues), keep it or drop it. The `interview` skill
reads the Inbox before its questions, so an item a plan touches becomes one of its open decisions;
it writes nothing, so the change that settles the item deletes it.

## Considered options

- `.about/todo/` — "todo" reads as work agreed on; most items are still to be decided.
- `review` in the name — the word is a Session review's, a Retro's and a code review's already.
- `triage` — the same sense, but jargon.
- A folder with a file per item — an item is a few lines, and deleting them is easier than a file.
- Bullets in place of headings — a draft decision's options don't fit in one.
- Items only in the Session review's reply, shown once at the next session start — one the user
  missed is lost.
- Writing where the project keeps its own todos or issues — the review would need a rule to find
  that place, and would write outside `.about/`.
- A proposed ADR and the glossary's `## Unresolved` (until 2026-10-01) — open items in three
  places, two of which read as settled, and nothing counted them.
- A Guideline rule only, with the review unchanged — the review would still drop a bug it saw.
- `tidy` dropping the settled items (until 2026-10-01) — nothing went through the rest; one skill
  does both now.
- Going through the Inbox unattended, as the Session review — an item is there because it needed
  the user.
- The count in the Status line — always in sight, but one more segment for a number that rarely
  changes.
- `architecture` reading the Inbox too — it works from decisions taken, not open ones.
- The item's format in one shared file the skills cite — the Session review's prompt and the
  Guidelines would still keep copies of their own.

## Consequences

- The name and the format are in every project that uses the plugin: changing them means
  migrating each one.
- An item nobody settles stays; the count at each session start keeps it in sight.
- The item's format is repeated in each text that adds items (`principles`, `adr`, `glossary`,
  `retro`, `inbox`, the Session review's prompt), since each is loaded on its own; changing it
  means changing them all.
- A project with a tracker has a second list; moving an item there is the user's call.
- Revisit when items pile up unread, or a project wants them in its tracker instead.
