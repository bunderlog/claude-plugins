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

## Whether a Retro looks for expensive tool calls

2026-10-01 · session review

A tool call that costs a lot of context is a Stall the `retro` skill doesn't look for: a huge
output, a whole file read where a part would do, an MCP server that spends many tokens. Another
project's retro skill lists it as a kind of its own. The skill can't look for it now: `condense`
reports repeated calls but not how large a call's output was, so the skill has nothing to read it
from.

Options:

- `condense` reports each call's output size, or the largest ones, and the skill gains an
  "Expensive calls" item in its "Look for" list.
- Leave it out: a Retro finds only the expensive calls that also show up as repeated ones.

Settled by: deciding whether it is worth the code in `condense`, with `baloo:adr`.
