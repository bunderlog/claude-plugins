# The CHANGELOG leaves out what a breaking change's footer tells users to do

2026-11-10

## Symptom

A Release's section in `CHANGELOG.md`, which its GitHub Release publishes as its notes (ADR
releases), lists a breaking change by its commit's subject only. What the commit's `BREAKING
CHANGE:` footer tells users to do is lost: 0.41.0's notes didn't say to install bagheera and pick
`bagheera:short-replies`, so a person who had `baloo:short-replies` set lost the style with no word
until 0.44.1. The section should carry the footer's text under the change it belongs to.

## Evidence

- Commit 3532a7e's body ends `BREAKING CHANGE: install bagheera (claude plugin install
  bagheera@bunderlog) to keep the Checks, …, and pick bagheera:short-replies in place of
  baloo:short-replies.`; CHANGELOG.md's 0.41.0 section lists only `split bagheera out of baloo:
  each person's session machinery, installed once (3532a7e)`.
- `src/release/release.py`, `_body`: each line is `- {scope}{description} ({sha})`; the footer is
  read only to mark the commit breaking (`_BREAKING_FOOTER`).

## Acceptance criteria

- A breaking change whose commit holds a `BREAKING CHANGE:` (or `BREAKING-CHANGE:`) footer is
  listed in its Release's section with the footer's text below its line, indented under it, the
  footer's wrapped lines joined into one paragraph.
- A breaking change marked only by `!` in its subject, and every feature and fix, is listed as
  before.
- In a Release of several plugins, the footer's text appears under the change in each plugin's
  part that lists it.
