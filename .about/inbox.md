# Inbox

What is still to consider (ADR inbox): one `## ` heading per item, deleted once settled.

## Whether the Stop check can check only what changed

2026-10-01 · session review

The Stop check runs one command on the whole repo (ADR stop-check). A real project had a lint
backlog of about 28,000 errors, so a whole-repo lint never passes there, and it wrote its own
script to lint only the changed lines. Its commits that only reformatted went through
`--no-verify` 25 times; with `no-git-hook-bypass` on, they could not have been made at all.

Options, none chosen:

- Leave it to the project: it names a command of its own that checks only what changed.
- Hand the command the changed files, or a base ref, so it can check only those.

Settled by: whether a second project needs it, and how the command would be told what changed.
