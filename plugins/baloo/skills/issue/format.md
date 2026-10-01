# Issue format

`.about/issues/<slug>.md`: what is wrong or what to do, in a few words (`export-drops-last-row.md`,
`retry-on-timeout.md`), kept stable, since commits and other files cite it ("Issue
export-drops-last-row"). An Issue in a tracker has the same title and parts, in the tracker's
markup, its comments as the tracker's own.

```md
# {What's wrong or what to do, in one line}

YYYY-MM-DD

## Symptom

{What happens and what should; for a task, the goal and why now.}

## Evidence

- {The steps to reproduce, a log line or error, the file and line, the version.}

## Acceptance criteria

- {Situation, action, expected outcome: one a test can pass or fail.}

## Comments

### YYYY-MM-DD · {cause | fix option | …}

{One comment per heading, oldest first.}
```

- Use the glossary's terms, capitalized as it does.
- Drop an empty section, but never Acceptance criteria.
