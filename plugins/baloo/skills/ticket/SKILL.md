---
name: ticket
description: Write a Ticket, a bug to fix or a task agreed to do — when the user asks to file, write or open an issue or ticket, or to move an Inbox item to the tracker. Searches for a duplicate first, puts the symptom, the evidence and the acceptance criteria in the description and the cause and the fix options in comments, and writes it to the tracker the project names, or to .about/tickets/<slug>.md. Not for what is still to decide, which is the Inbox's, or a feature's requirements, which are a PRD's.
---

# Ticket

You are writing work someone else can pick up without asking you. Make every part checkable;
don't just transcribe.

## Where

The tracker the project's CLAUDE.md or AGENTS.md names for tickets (a GitHub repo, a Jira project,
Linear), written through that tool's connector or command-line client. Without access to it,
stop: say what to set up, and offer the Ticket's text here. Without a tracker named,
`.about/tickets/<slug>.md` at the git repo's root, one Ticket per file ([format](format.md)), or
`.about/issues/` where the project already keeps them there. The project's own template or
conventions win.

## Before writing

- Search the tracker, or `.about/tickets/` and `.about/issues/`, for the same bug or task. If one
  exists, offer to add what is new as a comment to it instead.
- Read `.about/glossary.md` and `.about/adr/`: use the glossary's terms, and cite an ADR the work
  follows or would change. A Ticket against an ADR is a decision first: send it to the `adr`
  skill rather than filing it.
- What is still to decide (whether to fix it, which way) is an Inbox item, not a Ticket: say so
  and add it to `.about/inbox.md` instead: a `## <title>`, a line `<YYYY-MM-DD> · ticket`, then
  what it is and what would settle it.

## Write

- **Description**: what stays true however the cause turns out.
  - **Symptom**, for a bug: what happens and what should, as someone would see it. For a task,
    the goal and why now.
  - **Evidence**: the steps to reproduce, the log line or error, the file and line, the version.
    Mask anything that may be a secret.
  - **Acceptance criteria**: each one a test can pass or fail: the situation, the action, the
    expected outcome. A PRD's criterion it serves is linked, not copied. Leave out what every
    change must meet, such as the project's checks passing: the verifier only reads, so it can't
    mark one met, and `/louie:merge` then stops.
- **Comments**: the cause as far as it is known, and the options for a fix with their
  trade-offs, each its own comment, so a wrong guess is answered, not edited away.

Use the tracker's own markup. Before filing to a tracker, show the user the Ticket and file it once
they agree; then read it back and fix markup that shows as text instead of rendering.

## After

- Tell the user in one line where it is: its link, or its file.
- An Inbox item it came from is deleted, and the Inbox's file with its last item.
- In `.about/tickets/`, the change that does the work deletes the file; in a tracker, close the
  Ticket with that change. Don't commit.
