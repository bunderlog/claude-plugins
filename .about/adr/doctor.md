# The binary's `doctor` shows the plugin's state, run by the `doctor` skill, and changes nothing

Date: 2026-10-03

Session start says what it changed and what went wrong, but not what is on: which Checks run and
why, which Git hook runs which binary, which version runs. A Git hook running a link to an older
binary, with nothing saying so, went unnoticed in this repo. So the binary has `doctor`, which
shows the plugin's state in the repo it runs in, its problems first, each with what fixes it: the
binary running and the link the Git hooks and the Status line run (ADR git-hooks), the Config's
settings, each Check on or off and whether by its key or by default (ADR checks), each Git hook,
and the Guidelines on and off. It exits 1 when it finds a problem, 0 otherwise, and prints the
same text for the user and for Claude.

It only reads: what fixes a problem is the next session start, or a file or a Config key that is
the user's to change, which it names. The versions it compares are local, the running binary's
with the link's target; it asks GitHub for nothing.

The binary isn't on the PATH, so the `doctor` skill runs it through the Loader, as `retro` runs
`condense`, and answers the user's question from its output; Claude can run the skill when the
user asks what is on or why something didn't run.

## Considered options

- Only the command, run by hand — no description in every session's context, but nobody knows the
  link's path, or that the command is there.
- Session start printing the whole state every time — no new command, but every session pays
  tokens for what is rarely needed.
- Only the problems — shorter, but it doesn't answer "what is on?".
- `doctor --fix` — quicker for the user, but a second copy of what session start does.
- The latest GitHub Release beside the local versions — "update the plugin" said for the user, for
  a network call, its time and the API's limits, on every run.
- JSON output — one format for Claude to parse, but the user would read it too.

## Consequences

- Each new setting, Check or kind of problem session start can find needs a line in `doctor`
  too, or `doctor` shows less than is there.
- The skill's description is in every session's context.
- Revisit when a project's CI wants the state too: JSON or a flag would then pay for itself.
