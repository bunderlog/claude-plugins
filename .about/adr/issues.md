# Issues are written by a skill of their own, to the project's tracker or `.about/issues/`

Date: 2026-10-01

Users asked for tickets by hand: about 17 requests in 8 sessions of one project, each time over
several messages. The `issue` skill writes one Issue per request, a bug to fix or a task to do,
after a search for a duplicate. Its description holds the symptom, the evidence and the acceptance
criteria; the cause and the options for a fix go in comments, so the description stays true while
the guess about the cause changes. The project's own template wins.

Where it goes follows ADR prd: a tracker the project's `CLAUDE.md` or `AGENTS.md` names, written
through that tool's connector, the skill text naming no tool; without that connector, stop and
say which to set up. Without a tracker named, each Issue is `.about/issues/<slug>.md` (ADR
about-folder), its comments a section of the file, and the change that does the work deletes it,
as an Inbox item's settling change does; git keeps it.

An Issue is work already agreed; the Inbox holds what is still to decide, a bug found among it
(ADR inbox). So nothing writes an Issue unattended: the Session review and `principles` still send
a bug left for later to the Inbox, and the `inbox` skill's "file an issue" moves an item from
there. Session start doesn't count Issues: the count is for what waits on the user. The skill
writes one Issue a request and none from a PRD's criteria, which stay in one place (ADR prd).

## Considered options

- A `ship` skill beside it (branch, commit, push, `merge --ff-only`, delete the branch) — asked
  for in every session of one project, but the flow is each repo's own, and a Retro already
  recommends a project skill for a prompt typed again and again.
- `ticket` for the name — the `inbox` skill's word until now, and "issue" names a Stall's
  _Avoid_; but "issue" is what GitHub and Jira call it, and what users asked for.
- Only the ticket's text in the chat, filed by the user — no duplicate search, and no check that
  the markup renders.
- A Config key naming the tracker — rejected for PRDs already (ADR prd).
- Bugs written straight to `.about/issues/` by the Session review and `principles` — work created
  with nobody there to agree to it.
- Closed Issues kept with `Status: closed` — the folder fills with done work; git has it.
- Numbered files, `0007-slug.md` — easy to cite in a commit, but two branches take one number.
- Counting Issues at session start — code for a list the user already agreed to.
- Stories from a PRD's criteria — the criteria in two places, drifting apart (ADR prd).

## Consequences

- Without a tracker, a project's open work is in the repo, in `.about/issues/`, visible to any
  agent and to whoever clones it.
- An Issue nobody does stays unnoticed until someone looks: nothing counts them.
- Revisit when Issues pile up undone, or a Session review keeps sending the Inbox bugs the user
  then files unchanged.
