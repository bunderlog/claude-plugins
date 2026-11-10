# bagheera shows which of the machine's projects need attention, and what to do about each

## Problem

A person who works with Claude Code in several projects sees only the one in front of them: what
waits for them elsewhere waits until they happen to open it. On 2026-11-11, 4 Session reviews'
Proposals had waited in two projects since 2026-10-09 and 2026-10-29, unseen, since nobody opened a
session there; 2 repos were half set up (PRD setup); and a session in another terminal that stops
for an answer or a permission says so only in that terminal. PRD harness asks for such a project to
show, without opening it, in the Status line of a session in any project.

## Users

- Each person with bagheera installed: the Status line, where they set bagheera's (ADR
  status-line), and `doctor` show them their own machine's projects and sessions.
- Not for: a team seeing each other's machines, or one machine's projects from another (PRD
  harness). A person with a Status line of their own gets `doctor` alone.

## Success signal

On the maintainer's machine, no Proposal waits more than 7 days, from 4 waiting up to 33 days on
2026-11-11; and the maintainer, asked after a week of use, names a session they would have left
waiting without the line.

## Scope

- The machine's projects: for each Transcript file in Claude Code's config folder
  (`CLAUDE_CONFIG_DIR`, else `~/.claude/`), a subagent's included, modified in the last 30 days,
  the main working tree of the git repo holding the `cwd` its entries name. A subfolder counts as
  its repo, and a linked worktree as its main working tree, so a `deliver` worktree's sessions
  count for the project; a `cwd` that is gone, or in no repo, is left out.
- A project needs attention when any of these holds, each with what to do about it:

  | What | When | What to do |
  | --- | --- | --- |
  | Proposals wait | `.about/proposals/` holds a Proposal `doctor` counts as waiting or as a mismatch, deferred ones included | open a session there, which asks about each |
  | Setup lacks an item | the repo's `.claude/settings.json` turns baloo on, and `doctor` would name an item of PRD project-setup's list missing | `/bagheera:setup` there |
  | Git hooks off | git tracks Git hooks in one of the layouts PRD setup knows (`.githooks/`, `.husky/`), and this clone's `core.hooksPath` isn't that layout's | the command for its layout (PRD setup) |
  | Inbox not gone through | an item of `.about/inbox.md` whose first non-blank line after its heading doesn't end ` · kept <date>`, as baloo's session start counts them | `/baloo:inbox` there |
  | A session waits | a session a person runs ended its turn, asks for a permission, or asks a question (`AskUserQuestion`), and no prompt has followed, it hasn't ended, and its Claude Code still runs | switch to that session |

- A repo that isn't set up at all (its `.claude/settings.json` doesn't turn baloo on) isn't named
  for lacking items: PRD setup tells it so once per clone and nothing more, since its owner may
  have chosen not to. The other rows hold for it. `doctor` counts it, apart from the projects that
  need attention.
- A turn the person interrupted isn't waiting: they are at it. A headless session, a Session
  review's among them, and a subagent never wait.
- The Status line has little room, so it gives up its bars to make room for one short part:
  - The whole line is grey while all is well: the folder, the branch, the icons, the numbers and
    the model. Each Usage bar and the Cache bar becomes an icon and its number, which turn yellow
    or red together at the thresholds that color the bar today: `▤ 12% 120K` for the context, `◷ 42% 02:42` for the
    5-hour limit, `◷ 61% Sat` for the 7-day one, `↻ 40m` for the cache. The details after the
    number (tokens, reset times) stay grey and have no parentheses. A group's parts are a space
    apart, the groups a grey `·`, as Claude Code's own footer has them.
  - The part, before the model, names nothing: a yellow `⧗` and how many sessions wait, then a
    yellow `⚑` and how many projects need attention, each only when it isn't 0, since each shown
    is something to do. Which ones, and what to
    do, is `doctor`'s.
  - Where the line doesn't fit, the details go first, then the model; the part stays.
  - It leaves out the session it draws for, but not the other sessions or the needs of its own
    project.
- The line draws from what bagheera last found, at most 60 seconds old, and never waits for the
  check itself; ADR status-line and ADR doctor are rewritten with the change that builds this, and the
  glossary's Usage bar and Cache bar, which are no bars once it is built, renamed.
- `doctor`, in any folder, adds the machine's projects: each that needs attention, a line for each
  thing, with its folder and what to do, a waiting session's line saying since when it waits; then how many need nothing and how many aren't set up.
  They aren't `doctor`'s problems: its exit code stays about the repo it runs in, and outside a repo
  about the plugin and the person's settings alone.
- Both only read, apart from bagheera's data folder: no file in a project, no git config, no
  network.

## Non-goals

- Fixing anything from the Status line or `doctor`: the person runs the fix named (ADR doctor).
- A CI run that failed, an open pull request, or an Issue assigned: each needs `gh` or a tracker,
  which PRD harness doesn't require.
- Uncommitted or unpushed work: the session's own clone's is PRD status-line's, and baloo's
  session start tells the `.about/` files not committed.
- A sound or a desktop notification when a session waits: Claude Code's and the terminal's.
- A page or tool of its own for this (PRD harness, Considered options).
- A repo no session has worked in: it isn't one of the machine's projects.

## Anti-goals

- The Status line draws slower, goes blank, or shows an error because a check of the projects
  failed or is still running.
- A mark that never clears for what the person can't or won't change, so that it stops being read.
- A session the person is looking at, or a headless one, shown as waiting.

## Acceptance criteria

- Drawing the Status line runs no `git` in another project and reads no file of one; on the
  maintainer's machine, with 30 projects, it draws in under 300 ms. The second checked by hand.
- A repo with a Transcript modified 29 days ago is one of the machine's projects, one whose latest
  was modified 31 days ago isn't, nor is a `cwd` since removed; a `cwd` in a subfolder or a linked
  worktree counts for its repo's main working tree.
  → test: tests/bagheera/test_attention.py "Projects.test_projects"
- With the clock moved 60 seconds on after a Proposal is written in a project where nothing else
  needs attention, the line of a session in another project counts one more project and `doctor`
  names it; 60 seconds after the last one is decided, one fewer.
  → test: tests/bagheera/test_attention.py "Needs.test_proposals"
  → test: tests/bagheera/test_attention.py "Check.test_check_and_read"
- A repo whose `.claude/settings.json` turns baloo on but lacks `attribution` needs attention; a
  repo that isn't set up doesn't for it, and `doctor` counts it as not set up.
  → test: tests/bagheera/test_attention.py "Needs.test_setup"
  → test: tests/bagheera/test_doctor.py "Machine.test_machine"
- A clone where git tracks `.githooks/` and `core.hooksPath` is unset needs attention; 60 seconds
  after `git config core.hooksPath .githooks` runs there, it doesn't.
  → test: tests/bagheera/test_attention.py "Needs.test_hooks_off"
- An Inbox whose every item has ` · kept <date>` on the first non-blank line after its heading
  doesn't make its project need attention; one with an item that hasn't, does.
  → test: tests/bagheera/test_attention.py "Needs.test_inbox"
- 60 seconds after a session's turn ends, it asks for a permission, or it calls `AskUserQuestion`,
  the line of a session in any project counts it waiting, and `doctor` names its project; 60
  seconds after a prompt is sent to it, it ends, or its Claude Code exits without ending, it
  doesn't. Checked by tests that feed the Hooks' input; that Claude Code sends each event, by hand
  once.
  → test: tests/bagheera/test_cli.py "Waiting.test_marks"
  → test: tests/bagheera/test_attention.py "Waits.test_waits"
  → test: tests/bagheera/test_attention.py "Waits.test_exited"
- A session's own line never shows itself waiting, and an interrupted turn, a headless session
  (a Session review's included) and a subagent are never shown waiting.
  → test: tests/bagheera/test_attention.py "Waits.test_found"
  → test: tests/bagheera/test_cli.py "Waiting.test_headless"
- With three sessions waiting and two projects needing attention, the part is `⧗ 3 · ⚑ 2`; with
  none waiting, `⚑ 2`; with nothing needing attention, there is none. It holds no project's name.
  → test: tests/bagheera/test_statusline.py "Marks.test_marks"
  → test: tests/bagheera/test_cli.py "Waiting.test_line"
- In 120 columns, in `claude-plugins` on `main` with both counts, the line shows the folder, the
  branch, every number with its details, the part and the model; no bar is drawn at any width.
  → test: tests/bagheera/test_statusline.py "Marks.test_marks"
- In a line too narrow for all of it, the details go first, then the model, and the part stays; with
  nothing over a threshold and nothing waiting, every part of the line is grey; a context of 22%
  shows its icon and number in red, and its tokens grey.
  → test: tests/bagheera/test_statusline.py "Render.test_narrow"
  → test: tests/bagheera/test_statusline.py "Render.test_context_colors"
  → test: tests/bagheera/test_statusline.py "Marks.test_all_grey"
- `doctor` lists each project that needs attention, a line for each thing with its folder and what
  to do, and the counts of those that need nothing and of those not set up; in a repo with no
  problem of its own it exits 0 while other projects need attention, and outside any repo it lists
  them too.
  → test: tests/bagheera/test_doctor.py "Machine.test_machine"
- Neither the Status line nor `doctor` changes a file outside bagheera's data folder or git's
  config, checked by a test that compares each project's files and `git config --list` before and
  after; nor opens a socket, checked by a test that fails any.
  → test: tests/bagheera/test_attention.py "Check.test_reads_only"
- With no Transcripts, or a Transcript that can't be read, the line draws without the part and
  `doctor` says it found no projects.
  → test: tests/bagheera/test_attention.py "Projects.test_no_transcripts"
  → test: tests/bagheera/test_doctor.py "Machine.test_none_found"
