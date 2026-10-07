# What is still to consider waits in `.about/inbox.md` until something settles it

Date: 2026-10-07

A decision or a term still open, and a bug or a finding left for later, had no common place: a
proposed ADR, the glossary's `## Unresolved`, or nowhere, and Claude's auto-memory took some,
where a teammate never sees them. In one real project a Hook of its own wrote about 18 todos in
12 of 246 runs, and fix commits later closed several; in another, the user asked four times in
nine minutes to move what auto-memory held into git, and about 16 memory files repeated the
repo's own `docs/issues/`.

So each is an item of the Inbox, `.about/inbox.md` at the repo's root (ADR about-folder): a `##
<title>`, a line `<YYYY-MM-DD> · <source>` naming who added it, then what it is and what would
settle it. The Session review proposes to add what the conversation left open, or found and didn't
fix, for the user to accept (ADR session-review); `adr` and `glossary` add what stays open, `issue`
what is still to decide, `retro` each fix the user didn't pick, and a rule `principles` prints on
every task sends anything else left for later there, a code review's findings among them, rather
than to Claude's memory. An item is deleted once the code, an ADR, the glossary or the Guidelines
settle it: by the change that settles it, or by an accepted Proposal of the Session review where the
conversation did; the file goes with its last item, so a project with nothing open has none. Session
start tells Claude how many items there are, one per `## ` heading outside a code block, and how
many nobody has gone through yet, to tell the user, and that the `inbox` skill goes through them
with the user. The `interview` skill reads the Inbox before its questions, so an item a plan touches
becomes one of its open decisions; it writes nothing, so the change that settles the item deletes
it.

The `inbox` skill ranks every item by its text, by what waiting costs, then goes through a few at a
time: it drops those the code, an ADR, the glossary or the Guidelines already settle, and asks of
the rest whether to decide it now, fix it now, file an Issue (ADR issues), keep it or drop it,
applying each round's answers before the next. So a user with 200 items and time for six can stop,
and the next run picks up where they left off: a kept item's date line ends in
`· kept <YYYY-MM-DD>`, and kept items come only after every item nobody has gone through, the
oldest mark first.

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
- Each kept item asked again on the next run — with many items, the same ones come back first
  every time.
- Marks of what was gone through in the plugin's data folder — the item's format stays, but the
  marks are one machine's, unseen in the file and by the team.
- Checking every item against the code before the first question — the costliest step, spent
  again on each run for items the user won't reach.
- A kept mark that expires after a set time, or kept items only on request — one more number to
  tune, or items nobody ever looks at again.
- The item's format in one shared file the skills cite — the Session review's prompt and the
  Guidelines would still keep copies of their own.

## Consequences

- The name and the format are in every project that uses the plugin: changing them means
  migrating each one.
- An item nobody settles stays; the count at each session start keeps it in sight.
- Only the `inbox` skill writes the kept mark; another text that adds to a kept item leaves it, so
  what it added waits until the kept items' turn.
- The item's format is repeated in each text that adds items (`principles`, `adr`, `glossary`,
  `issue`, `retro`, `inbox`, the Session review's prompt), since each is loaded on its own;
  changing it means changing them all.
- A project with a tracker has a second list; moving an item there is the user's call.
- Revisit when items pile up unread, or a project wants them in its tracker instead.
