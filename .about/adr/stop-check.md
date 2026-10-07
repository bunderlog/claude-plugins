# The Stop check is removed: it never caught a failure the agent would have left

Date: 2026-10-07

baloo has no Stop check: nothing runs the project's checks when Claude ends a turn. A failure is
caught by the project's own Git hooks and CI, and "Done is verifiable" in `principles` asks Claude
to run them itself. A Config that still has `stop-check` works as without it: the key is ignored,
and `doctor` names it for the user to delete (ADR measurement).

## Considered options

- The Stop check (until 2026-10-07): where the Config named a command, `stop-check: mise run
  check`, the binary ran it when Claude ended a turn that changed the working tree, and handed a
  failure back to Claude to fix, once a turn. Measured over about three weeks on two machines
  (ADR measurement), it never blocked for real: its one block was a deliberate probe, one project
  turned it off in its Config, and without it Claude still left no red tests, 0 to 2 turns ending
  red, both for the environment, not the code. Its cost
  was a Hook and a snapshot of the working tree at every prompt, and a run of the command after
  every turn that changed a file.
- The project's own Stop Hook in `.claude/settings.json` — the way for a project that wants one;
  it runs after every answer, questions too.
- A reminder, handed to Claude at the turn's end — nothing tells whether Claude acted on it, and
  it is one more ceremony after each edit.

## Consequences

- A turn can end with a check red; the commit's Git hooks or CI then fail on it.
- The `UserPromptSubmit` Hook stays, for the Loader's download after an update (ADR binary).
- Revisit when sessions show turns ending red that a check at the turn's end would have caught.
