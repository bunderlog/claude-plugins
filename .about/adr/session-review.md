# A Session review records, after each session, what it settled but nobody wrote down

Date: 2026-10-01

A session often settles a term or a decision that nobody records, and it is lost when the session
closes. Where the Config has `session-review: true`, the `SessionEnd` Hook runs the binary's
`session-end`, which starts a Session review and returns at once: a separate headless `claude -p`,
detached so that Claude Code's exit never waits for it, run at the repo's root with the
`glossary` and `adr` skills. It loads the plugin from its own folder too, since the review's
session may not have it otherwise, as where the ended session had it from `--plugin-dir`. A new
Config turns it on; without the key it is off, since it didn't exist before the key (ADR config).

The review reads only the user's and Claude's text, masked as a Retro's is (ADR transcripts),
and at most the last 200,000 characters of it: no tool call or result. It skips a session shorter
than 2,000 characters, which can't have settled much, and a headless one, its own or another
tool's, and a review never starts another. It may edit only `.about/glossary.md`, `.about/adr/`
and `.about/inbox.md`: its tools are limited to reading and editing, anything not allowed is
denied rather than asked, and it never commits. Only what the conversation clearly agreed, and
only about the repo it runs in, is recorded. Anything contested or left open, and a bug or a
problem the session found but didn't fix, is an item of the Inbox, and an item the conversation
settled is deleted (ADR inbox). It never edits a PRD, an agreement with the user about what to
build.

Its session changes nothing else either: there session start creates no Config, picks no Output
style, sets no Status line and writes no Git hook, and no Stop check or Format on edit runs. A
review starts as the user may be opening their next session, whose session start writes the same
settings files. The Checks a Hook runs still run there, so a tool call of the review's can't show
it a Secret; session start still names the Guidelines.

Its reply and process id are kept per repo in the plugin's data folder. The next session start
tells Claude, once, to tell the user what the last review changed, or that it is still running.
It runs with the user's default model.

## Considered options

- Only the glossary and the ADRs (until 2026-10-01) — a bug the session found and didn't fix was
  lost with it.
- Dropping it, since most reviews change nothing — the few that do record what would otherwise
  be lost, and that is what it is for.
- Session start as in any other session but for the Git hooks (until 2026-10-01) — nothing
  needed its writes there, and they could race those of the user's next session.
- The Checks a Hook runs off in its session too, so nothing of the plugin runs there — a Read of
  an Env file by the review would go unchecked.
- Off in a new Config too — no tokens without asking, but no review until someone knows to ask.
- Handing over the conversation unmasked — a Secret the user pasted, or Claude repeated, would
  reach one more session and Transcript.
- A cheaper model, pinned — less cost per session, but a subtle decision is more likely missed or
  recorded badly.
- A key for the model — one more setting, for a choice nobody has asked to make.
- Its state in the system's temporary folder under predictable names — shared with every other
  user and process on the machine.

## Consequences

- Every session with a new Config costs a headless run when it ends, most of them changing
  nothing.
- Its edits appear in the working tree unannounced until the next session start; they are the
  user's to review and commit.
- It can edit the glossary, an ADR or the Inbox while the next session in the repo is already
  running.
- A decision the conversation masked (a long id) can't be recorded exactly.
- Revisit when a review records something wrong or about another repo, or its cost shows.
