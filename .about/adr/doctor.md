# The plugin's `doctor` shows its state, run by the `doctor` skill, and changes nothing

Date: 2026-10-14

Session start says what it changed and what went wrong, but not what is on: which Checks run and
why, which Git hook runs which version, which version runs. A Git hook running a link to an older
binary, with nothing saying so, went unnoticed in this repo. So the plugin has `doctor`, which shows
its state in the repo it runs in, its problems first, each with what fixes it: the plugin's folder
and version running and the link the Git hooks and the Status line run (ADR git-hooks), the Config's
settings, whether a Session review runs and how many Proposals wait or disagree with their files
(ADR session-review), each Check on or off and whether by its key or by default (ADR checks), each
Git hook, and the Guidelines on and off; a setting an earlier Release had and this one removed is
one of its problems, for the user to delete, which session start leaves out (ADR measurement). It
exits 1 when it finds a problem, 0 otherwise, and prints the same text for the user and for Claude.

It only reads: what fixes a problem is the next session start, or a file or a Config key that is the
user's to change, which it names. The versions it compares are local, the running plugin's with the
link's target and with the one Claude Code records as installed for the project, in its own
folder's `plugins/installed_plugins.json`; it asks GitHub for nothing. Claude Code loads a plugin
only when it starts, so a session started before an update runs the version before for hours: on
2026-10-14 a project ran 0.24.1 and 0.21.1 for a week with 0.25.1 installed. A newer version
installed is a problem a restart fixes, and the next prompt in such a session tells Claude, once,
to tell the user; that file is Claude Code's and undocumented, so a shape it can't read says
nothing.

The plugin isn't on the PATH, so the `doctor` skill runs it as `python3 -E -s
<plugin>/scripts/run.py doctor`, as `retro` runs `condense` (ADR binary), and answers the user's
question from its output; Claude can run the skill when the user asks what is on or why something
didn't run. With `doctor` showing the version, session start no longer shows it to the user (until
2026-10-03 its `systemMessage`, `baloo <version>`), and prints nothing where it has nothing to tell
Claude.

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

- Asking GitHub for the latest Release — it would name an update the user hasn't installed, at a
  call per session; what was installed and not yet run is the gap.

## Consequences

- Each new setting, Check or kind of problem session start can find needs a line in `doctor`
  too, or `doctor` shows less than is there.
- The skill's description is in every session's context.
- Revisit when a project's CI wants the state too: JSON or a flag would then pay for itself.
