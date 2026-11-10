# A Session review proposes only what a session settled

## Problem

The Session review proposes what a session settled and what it left open, and the open part
floods the Inbox: in `webui`, 71 of its 116 items came from it, mostly questions nobody returns to,
while what it is for, a decision or a term the session agreed and nobody wrote down, is 58% of
what later surfaced again (ADR session-review, ADR measurement).

## Users

- Everyone in a project with baloo on: the Proposals they are asked about are decisions.
- Not for: someone who wants every open question written down; they add it to the Inbox
  themselves, or ask Claude to.

## Success signal

A Session review adds no item to any project's Inbox; the share of its Proposals accepted rises.

## Scope

- A Session review proposes a change to the glossary, an ADR or a PRD that the conversation
  settled, and the deletion of an Inbox item the conversation settled; nothing for what it left
  open, contested or found and didn't fix.
- A Proposal for the Inbox, an earlier review's or one a review still writes, is shown and decided
  as before, and the `inbox` skill still goes through it: the rule is the review's prompt, not a
  check on its file.

## Non-goals

- Moving the Session review to bagheera: Issue split-bagheera-louie.
- Asking the user whether to write an open question down: the session itself can.

## Anti-goals

- A decision the session settled is lost because the review now proposes less.

## Acceptance criteria

- The prompt a Session review runs with asks for changes to the glossary, ADRs and PRDs, and for
  the deletion of a settled Inbox item, and tells it to propose nothing for what is open.
  → test: tests/bagheera/test_review.py "test_only_what_was_settled"
- In an eval session that settles a term and leaves a question open, the review proposes the term
  and nothing for the question.
