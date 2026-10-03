---
name: issue
description: Write an Issue, a bug to fix or a task agreed to do — when the user asks to file, write or open an issue or ticket, or to move an Inbox item to the tracker. Searches for a duplicate first, puts the symptom, the evidence and the acceptance criteria in the description and the cause and the fix options in comments, and writes it to the tracker the project names, or to .about/issues/<slug>.md. Not for what is still to decide, which is the Inbox's, or a feature's requirements, which are a PRD's.
---

# Issue

You are writing work someone else can pick up without asking you. Make every part checkable;
don't just transcribe.

## Where

The tracker the project's CLAUDE.md or AGENTS.md names for issues (a GitHub repo, a Jira project,
Linear), written through that tool's connector or command-line client. Without access to it,
stop: say what to set up, and offer the Issue's text here. Without a tracker named,
`.about/issues/<slug>.md` at the git repo's root, one Issue per file ([format](format.md)). The
project's own template or conventions win.

## Before writing

- Search the tracker, or `.about/issues/`, for the same bug or task. If one exists, offer to add
  what is new as a comment to it instead.
- Read `.about/glossary.md` and `.about/adr/`: use the glossary's terms, and cite an ADR the work
  follows or would change. An Issue against an ADR is a decision first: send it to the `adr`
  skill rather than filing it.
- What is still to decide (whether to fix it, which way) is an Inbox item, not an Issue: say so
  and add it to `.about/inbox.md` instead: a `## <title>`, a line `<YYYY-MM-DD> · issue`, then
  what it is and what would settle it.

## Write

- **Description**: what stays true however the cause turns out.
  - **Symptom**, for a bug: what happens and what should, as someone would see it. For a task,
    the goal and why now.
  - **Evidence**: the steps to reproduce, the log line or error, the file and line, the version.
    Mask anything that may be a secret.
  - **Acceptance criteria**: each one a test can pass or fail: the situation, the action, the
    expected outcome. A PRD's criterion it serves is linked, not copied.
- **Comments**: the cause as far as it is known, and the options for a fix with their
  trade-offs, each its own comment, so a wrong guess is answered, not edited away.

Use the tracker's own markup. Before filing to a tracker, show the user the Issue and file it once
they agree; then read it back and fix markup that shows as text instead of rendering.

## After

- Tell the user in one line where it is: its link, or its file.
- An Inbox item it came from is deleted, and the Inbox's file with its last item.
- In `.about/issues/`, the change that does the work deletes the file; in a tracker, close the
  Issue with that change. Don't commit.
