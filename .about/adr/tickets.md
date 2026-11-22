# Tickets are written by a skill of their own, to the project's tracker or `.about/tickets/`

Date: 2026-11-22

Users asked for tickets by hand: about 17 requests in 8 sessions of one project, each time over
several messages. The `ticket` skill writes one Ticket per request, a bug to fix or a task to do,
after a search for a duplicate. Its description holds the symptom, the evidence and the acceptance
criteria; the cause and the options for a fix go in comments, so the description stays true while
the guess about the cause changes. The project's own template wins.

Where it goes follows ADR prd: a tracker the project's `CLAUDE.md` or `AGENTS.md` names, written
through that tool's connector or command-line client (`gh`), the skill text naming no tool; without
access through either, stop and say what to set up. Without a tracker named, each Ticket is
`.about/tickets/<slug>.md` (ADR about-folder), its comments a section of the file, and the change
that does the work deletes it, as an Inbox item's settling change does; git keeps it. A project
that kept them in `.about/issues/`, their folder before 0.68.0, keeps them there: session start
lists both folders, and the skill writes to the one the project has.

A Ticket is work already agreed; the Inbox holds what is still to decide, a bug found among it
(ADR inbox). So nothing writes a Ticket unattended: the Session review and `principles` still send
a bug left for later to the Inbox, and the `inbox` skill's "file a ticket" moves an item from
there. Session start lists each Ticket by its title, with the ADRs and PRDs (PRD index), but
doesn't count them: a count is for what waits on the user. The skill
writes one Ticket a request and none from a PRD's criteria, which stay in one place (ADR prd).
A Ticket's acceptance criteria hold only what its own change does, never what any change must,
such as the project's checks passing: a verifier can't mark that one met, so `/louie:merge` stops
on it, and `implement` and `merge` run the checks anyway.

louie's `implement` Workflow takes a Ticket from there to a pull request (PRD implement), or up to
five, all planned before any is built (PRD batch): it reads the Ticket, branches, commits, pushes
and opens the pull request, each repo's flow coming from what the project names, its checks command,
commit format, tracker and code host, rather than from the plugin. It never merges and never closes
a tracker's Ticket; a Ticket in `.about/tickets/` goes with the change that delivers it, as above.
louie merges a pull request only through `/louie:merge` (PRD merge), on the person naming it: one
at a time, each rebased onto the default branch and checked again first, by the merge method the
project names. Closing a tracker's Ticket stays the person's.

## Considered options

- A `ship` skill beside it (branch, commit, push, `merge --ff-only`, delete the branch) — asked
  for in every session of one project, but the flow is each repo's own, and a Retro already
  recommends a project skill for a prompt typed again and again. `implement` stops at the pull
  request, and takes the flow from what the project names. Merging became a Workflow of its own,
  `merge`, once pull requests built from one default branch conflicted when merged one by one:
  its merge method and checks too come from what the project names, not from the plugin.
- `issue` for the name, until 0.68.0 — what GitHub and Jira call it, but read as a problem
  rather than work to do, and already a Stall's _Avoid_; `ticket` is neutral between a bug and a
  task, and known to any tracker's user. `task` is taken by Claude Code's tasks and a Workflow's
  `task-notification`.
- `ticket`, `task`, `issue` or `deliver` for the Workflow's name — the first two name what it
  takes, `task` only one kind of Ticket, and `deliver`, its name until 0.68.0, what reaches users,
  where it stops at a pull request; `implement` names what it does with a Ticket, as its agent
  `louie:implementer` does.
- Only the ticket's text in the chat, filed by the user — no duplicate search, and no check that
  the markup renders.
- A Config key naming the tracker — rejected for PRDs already (ADR prd).
- Bugs written straight to `.about/tickets/` by the Session review and `principles` — work created
  with nobody there to agree to it.
- Closed Tickets kept with `Status: closed` — the folder fills with done work; git has it.
- Numbered files, `0007-slug.md` — easy to cite in a commit, but two branches take one number.
- Counting Tickets at session start — code for a list the user already agreed to.
- Stories from a PRD's criteria — the criteria in two places, drifting apart (ADR prd).

## Consequences

- Without a tracker, a project's open work is in the repo, in `.about/tickets/`, visible to any
  agent and to whoever clones it.
- A Ticket nobody does is only listed at session start: nothing counts it or says it waits.
- Revisit when Tickets pile up undone, or a Session review keeps sending the Inbox bugs the user
  then files unchanged.
