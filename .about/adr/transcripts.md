# A Retro reads Transcripts only through the binary's condenser, which masks Secrets

Date: 2026-10-01

A Transcript keeps every tool call's full output, so it can hold a Secret a Check missed. The
`retro` skill reads Transcripts only through the binary's `condense`, never the raw file, so a
Retro doesn't Leak that Secret into one more context and Transcript. `condense` keeps what a Retro
needs: the user's prompts and commands, failed and refused tool calls, interrupts, repeated
calls and expensive ones; a denial by a Check is known by its `baloo:<check>:` prefix.

A call's cost is the tokens it added to the context, read from the `usage` Claude Code records
with the next response: what Anthropic counted, in tokens, not dollars. A session's report names
its largest calls, and a summary of several sessions the tokens per tool, so an MCP server that
spends a lot in small calls shows too. What came back before that response, the results of
calls made in parallel and Claude Code's own attachments, shares its growth by length, so a call
is charged only its own result's part. To look at one moment, the
skill asks it for the lines around it, in full but masked. Headless sessions, sessions where only
`/clear` was typed and subagents' Transcripts are left out.

`condense` masks in two passes: first each kind of Secret `no-secrets-in-commits` knows, then
anything shaped like one: a long run of letters and digits mixed, or a private key block. The
first catches a known key however short; the second, one of a kind no list has yet.

`no-secrets-in-context` doesn't deny reading a raw Transcript: that would also stop looking into
one for anything else, a grep that only counts lines too. The rule rests on the skill's text.

When a Stall's cause is in baloo itself, such as a Check's false alarm or a skill's rule, a Retro
writes out an issue to file on `bunderlog/claude-plugins` rather than a change: a project's copy of
the plugin is replaced by its next Release. In this repo, the plugin's own, it makes the change.

## Considered options

- The condenser as a TypeScript script run with `bun` — `bun` would have to be on every machine
  (ADR binary).
- Masking by shape only — a short token, or one without digits, would still show.
- Masking only the kinds `no-secrets-in-commits` knows — one of an unknown kind would show.
- A call's size in characters — simple and exactly one call's, but only an estimate of tokens.
- Dollars, from a price table in the binary — stale with each new model or price, and nothing on
  a subscription is paid per token.
- `no-secrets-in-context` denying reads of `~/.claude/projects/**/*.jsonl` — no Secret would come
  back by any path, but every other look into a Transcript would be denied too.

## Consequences

- Nothing stops Claude reading a raw Transcript but the skill's text.
- A long id that mixes letters and digits is masked too; a password of letters only still shows.
- Revisit when a Retro is found to have read a raw Transcript, or a Secret shows through the mask.
