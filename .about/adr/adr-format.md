# ADRs are edited in place, one per subject; only a draft has a Status

Date: 2026-10-01

An ADR, `.about/adr/<subject>.md` (ADR about-folder), holds the decisions on one subject as they
stand now. When one changes, the ADR is edited in place and its Date set to today; the choice it
drops moves to Considered options, marked `(until <date>)` with why, so the file still warns
against it. Git keeps every earlier version. The Check `no-stale-adr-date` (pre-commit) fails when
a staged edit changes an accepted ADR but not its Date, unless that Date is already today's, so an
unattended edit, such as the Session review's, shows as a change (ADR checks).

An ADR has a Status line only while it is a draft: `Status: proposed`. Without one it is accepted.
ADRs have no numbers: the file is named for its subject and cited as "ADR <subject>".

## Considered options

- Immutable ADRs, each changed decision a new ADR that supersedes the old one — one decision
  spread over a chain, and the ADRs and code comments citing an old one point at a replaced
  decision.
- Immutable ADRs whose Status lists the later ones that change part of them
  (`accepted, narrowed by …`) — a pointer, but still a chain to read.
- Immutable only once pushed, comparing with the upstream branch — pushing is not a step every
  project has.
- A Hook on Claude's file edits in place of a Git hook — Bash (`sed -i`, `cat >`) goes around it,
  and it misses edits made without Claude.
- No check — nothing would mark an ADR the Session review changed.
- A Date that changes with every edit — a second edit on the same day could never be committed.
- The date of the last commit to touch the ADR in place of today's — CI on a later day would
  agree, for one more git call and a rule harder to state.
- No Date, since git records when an ADR changed — a reader without git (the raw file, the
  Session review's headless session) would see nothing.
- Numbered files, `NNNN-slug.md` — the usual convention, and a number survives a rename; but with
  ADRs edited in place nothing points at a number, a file's number no longer dates its decisions,
  and "ADR 0005" says less than "ADR checks".
- `Status: proposed | accepted` on every ADR — the line almost always says accepted.
- No Status at all — the simplest file, but a decision still open would have nowhere to wait as a
  draft that `no-stale-adr-date` and the next session leave alone.

## Consequences

- What was decided on a given day, word for word, is in git, not in the file.
- A second edit on the Date's day passes unflagged, the Session review's among them; the diff
  still shows it.
- Nothing stops an edit that rewrites a decision's reasoning; reading the diff before a commit
  does. The Session review never commits.
- An ADR grows with its subject's decisions. A new one still open is a proposed ADR of its own
  until it settles and is merged into the ADR on its subject.
- Renaming a subject means updating its citations (`git grep "ADR <subject>"`).
- Revisit when a Status other than proposed comes back, such as a decision reversed but kept.
