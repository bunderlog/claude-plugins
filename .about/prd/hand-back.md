# Claude takes the steps it can take itself, and hands the user only what is theirs

## Problem

Claude asks the person to do a step it could do with a tool of its own session: run a command,
look a state up, retry a call. Each one costs a round trip, often while the person is busy
elsewhere, and the work waits on them. In the 30 days to 2026-11-18, of 137 Transcripts on the
maintainer's machine, the person ran with `!` a command Claude's reply had just named 46 times: 18
after Claude's own call of it was refused, 2 after one that ran, and 26 with no call of it tried
at all (`mise run`, `git push`, `claude plugin`, `pnpm`, `brew`). The one rule against it is in the maintainer's own
auto-memory, which nobody else's session sees.

## Users

- Everyone whose sessions run with louie on: the rule is louie's.
- bunderlog's maintainer, who decides from the Assessment and a Retro whether the rule pays off.
- Not for: a step only the person can take, or one theirs to decide. Those stay with them.

## Success signal

The Assessment's Hand-backs in the first 30-day window after the Release that ships this, on the
maintainer's machine, fall from 26 in 137 sessions (19 in 100) to 6 in 100 sessions or fewer, and
no Retro in that window finds Claude stuck on a step that needed the person.

## Scope

- A rule in `principles`' "On every task", which session start prints whole in every session
  (ADR guidelines): before giving the person a step, Claude takes it itself when a tool of the
  session can. It hands over only:
  - a step that needs the person: a password or passphrase, a login in a browser, a prompt a
    command waits on, a device or account only they can reach;
  - a step that is theirs to decide (a push, a Release, a deploy, anything outward-facing or hard
    to undo): Claude asks in a line and runs it on a yes, rather than giving the command to run.
  - a step whose call was refused, by the person, a permission rule or auto mode: as now, Claude
    says what was refused and doesn't reach the same effect another way.
- A Hand-back, a term for the glossary: a turn of the person's that runs a command with `!` (its
  text `<bash-input>…</bash-input>` in the Transcript), where the text Claude wrote since the
  person's turn before holds that command, and no Bash call of Claude's own since then holds it.
  Several `!` turns after one reply each count. Where such a call's result was refused (by the
  person, a permission rule, auto mode or a Check: `condense`'s `rejected`, `permission`,
  `classifier` and `check`), it counts apart, as after a refusal; a call that ran, even one that
  failed, counts neither. A subagent's or a Workflow's calls are not Claude's own here. A command
  starting with `sudo` is no Hand-back, as the Bash tool can't answer its password prompt; one
  theirs to decide, such as `git push`, is, as Claude should have asked and run it.
- The glossary's Stall says a step theirs to decide stays a Stall when Claude handed over running
  it: the decision is the person's, the command isn't.
- The Assessment counts, per session, the Hand-backs and those after a refusal, and reports each
  under louie as its total and the sessions it covers, naming this PRD, with the window before
  beside it (PRD assessment). A record holds the counts, zero too, never the command.
- `condense` marks such a `!` turn a Hand-back, or after a refusal, in place of a prompt, with its
  `[line]` and its command masked as any call's is, and the Retro skill looks for them as Stalls:
  what Claude could have run, or the permission rule that would have let the refused call through.

## Non-goals

- Counting a step handed over in words only ("open the dashboard", "check the log"): the rule
  covers it, the count doesn't, as it would take a model to judge (PRD assessment).
- Counting a prompt such as "do it yourself": 4 in the same 30 days, and its wording varies by
  language.
- A Check or a Hook that stops a Hand-back as it happens: a Check only denies a tool call (ADR
  checks), and a Hand-back is a reply.
- Changing what Claude Code's permissions or auto mode allow.
- An eval case before the rule, which ADR evals asks for: a case needs Claude to run a command,
  which the eval sandbox doesn't yet (Inbox, the item on verify's cases). The rule ships on the
  Assessment's figure, and its case comes once the sandbox runs Bash.

## Anti-goals

- Claude runs an outward-facing or irreversible step without the person's yes, to avoid handing
  it over.
- Claude reaches a refused call's effect another way, to avoid handing it over.
- Claude stalls on a command that waits for input it can't give, a password prompt or a pager,
  where handing it over at once was right.

## Acceptance criteria

- In a repo with louie on, session start's context holds the rule in "On every task", with the
  words "needs the person", "theirs to decide" and "refused".
- A session where Claude's reply names `mise run check` and the person's next turn is `! mise
  run check`, with no Bash call in Claude's turn, counts 1 Hand-back; with a Bash call of
  `mise run check` in that turn that was refused, 0 Hand-backs and 1 after a refusal; with one
  that ran, 0 and 0.
- A `!` command that Claude's last reply didn't name, one that named only part of it (`mise
  run` named, `! mise run check` run), and `! sudo tmutil addexclusion x` after a reply naming it
  count no Hand-back; `! git push` after a reply naming it counts 1.
- A session with 2 Hand-backs whose commands hold `AKIAIOSFODNN7EXAMPLE` adds a record holding
  neither command.
- The report shows Hand-backs and after a refusal under louie, each naming PRD hand-back, with
  the window before in brackets; a record of the Release before is counted again while its
  Transcript is on disk, and the figure says how many sessions it covers.
- `condense` on that first session marks the `!` turn a Hand-back with its `[line]`; the Retro
  skill's "Look for" names Hand-backs.
