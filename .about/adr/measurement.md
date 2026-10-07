# baloo keeps what a measurement of its use confirmed, and drops what only added friction

Date: 2026-10-07

baloo was built on the thesis that enforcing the rules in code, in Hooks and Git hooks, is a niche
of its own beside the project's knowledge. A measurement of how baloo was actually used checked
each part against that thesis, and the parts nothing confirmed are removed.

How it was measured, so it can be run again: the source is Claude Code's session Transcripts, one
JSONL file per session, of about three weeks up to 2026-10-07 on two machines, with baloo and
without; the scripts that read them are kept outside this repo. A session is baloo's where its
session start's context names the plugin; a Session review's own session is told by its
`sdk-cli` entrypoint and its first prompt, and left out of every other count. The events and what
counts for each:
- A Stop check block: the Stop Hook's summary records a block. It counts as real unless the
  failure was planted to test the Hook.
- A red turn: a turn with a test or check command that failed; it ended red when no later run of
  it in the turn passed. Its cause, the code or the environment, is read from the output.
- A Check's denial or question: a tool call's result, or the permission question, whose reason
  starts with `baloo:<check>:`. What followed: for a question, the user's answer; for a denial,
  a fix, nothing, or the same files changed by another command later in the turn ("the same
  effect another way").
- A Git hook's failure: a commit or push whose output starts with `baloo:<check>:`; it was fixed
  when the next commit or push passed without a flag that skips the Git hooks.
- A Guideline read in time: a Read of the Guideline's file before the first edit of a file on its
  subject, out of the sessions with such an edit; `.about/` read in time, the same before the
  first edit to code.
- A Session review's change: each term, ADR decision or Inbox item its edits add, change or
  delete. It was committed when its text reached a commit within seven days (`git log -p --
  .about`); its report was seen when the next session start of the user's in that repo showed
  it; lost when the next review replaced it first, or another headless session's start took it;
  used when a later session's text named the term, decision or item it recorded.

What it found:
- The Stop check never blocked for real: its one block was a deliberate probe, and one project
  turned it off in its Config. Without it Claude still
  left no red tests: 0 to 2 turns ended red, both for the environment.
- The questions, before a change to the Config or to Claude Code's settings that may turn the
  Hooks off, and `no-destructive-commands`' own: the user allowed 11 of 12. Friction, not
  protection.
- `no-destructive-commands`' denials: Claude reached the same effect another way twice, and
  Claude Code's auto mode classifier refuses the same commands itself.
- Working: the Git hooks (`conventional-commits`, `linear-history`, `no-stale-adr-date` each
  caught a commit that was then fixed), `no-secrets-in-context`, and `no-git-hook-bypass`, which
  stopped a push that would have skipped the Git hooks.
- The Guidelines were read before an edit on their subject in 5 of 79 cases, and in one project
  in 0 of 29, though session start named them all.
- The Session review: of its 80 changes in other repos, 64 were Inbox items; it wrote them
  straight into `.about/` with no approval; the next review overwrote 21 of its reports, and a
  headless reviewer of commits run by a project's pre-commit took 9; of 20 reviews whose report
  the user never saw, the changes of 19 were committed anyway. What it recorded came up in a
  later session in 58% of cases, the one sign of use.

So:
- The Stop check is removed (ADR stop-check).
- `no-destructive-commands` is removed, and so is every question a Check asked: a Check only
  denies (ADR checks).
- The Git hooks, `no-secrets-in-context`, `no-git-hook-bypass`, the knowledge skills, the Session
  review and the Guidelines stay; the Session review's approval and report, and how the
  Guidelines reach Claude, are reworked on their own.
- With the thesis unconfirmed, there is no plugin per role (ADR plugin).

A Config that still has a removed setting, `stop-check` or `claude-hooks.no-destructive-commands`,
works as without it: the binary ignores it, session start says nothing of it, and `doctor` names
it for the user to delete (ADR config, ADR doctor).

## Considered options

- Turning the parts off by default and keeping their code — no Config breaks, but code, tests and
  docs kept for parts the measurement found nothing for.
- Narrower questions, such as only before a change to the Config that turns a Check off — fewer
  questions, but the user said yes to 11 of 12 already, so fewer would still be said yes to
  unread.
- `no-destructive-commands` as denials only — Claude reached the same effect another way, and
  Claude Code's auto mode already refuses the same commands.
- A removed setting reported at every session start, as a key that isn't a setting is — every
  session in that repo pays for a fix made once; `doctor` is where the plugin's state is asked
  for.
- Waiting for more data — the Stop check's and the questions' figures pointed one way from the
  start, and every week they stay costs a Hook run per turn and a question said yes to.

## Consequences

- baloo no longer stops a command that destroys work, or asks before a change that turns its
  Checks off: Claude Code's permissions and auto mode are what stand there.
- A turn can end with a check red; the commit's Git hooks or CI catch it.
- A Config from an earlier Release keeps its removed keys until someone runs `doctor` and
  deletes them.
- The measurement is one user's, on their own projects; its figures are small.
- Revisit when a session shows work destroyed, a Leak, or a red turn that a removed part would
  have stopped, or when the measurement is run again.
