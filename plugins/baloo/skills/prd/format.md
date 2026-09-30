# PRD format

`.about/prd/<feature>.md`: the feature in a word or two (`export.md`, `sso-login.md`), kept
stable, since other files cite it ("PRD export"). A page in a tracker has the same title and
sections, and names its epic under the title.

```md
# {The feature, in one line}

Status: proposed

## Problem

{Whose pain, and why now, in one or two sentences.}

## Users

{Who it is for, and anyone it is deliberately not for.}

## Success signal

{What moves, from what to what, by when; or the qualitative signal.}

## Scope

- {What's in, the smallest version first.}

## Non-goals

- {What someone will assume is included, and isn't.}

## Acceptance criteria

- {Situation, action, expected outcome: one a test can pass or fail.}
  → test: {file} "{test name}", once it is built

## Open questions

- {What's undecided, and who or what settles it.}
```

- Use the glossary's terms, capitalized as it does.
- Leave out how it is built: that belongs to ADRs and the code.
- Drop an empty section, but never Acceptance criteria.
