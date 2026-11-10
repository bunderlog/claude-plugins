# The Status line shows the session's work not yet committed or pushed, and when to restart

## Problem

What a session leaves undone in its own clone, and what it runs, shows only when someone asks: a
file changed and not committed, or a commit not pushed, in a `deliver` worktree or on the branch in
front of the person, waits for `git status`; and a session that runs an older bagheera than is
installed tells only Claude, through a Hook's text, which Claude may or may not pass on (on
2026-11-11 a session here ran 0.51.1 with 0.52.0 installed).

## Users

- Each person who set bagheera's Status line (ADR status-line).
- Not for: a person with a Status line of their own; `git status` and `doctor` tell them the same.

## Success signal

The maintainer, asked after a week of use, names a commit, push or restart the line made them
do that they would otherwise have done later or not at all.

## Scope

- In the folder the line shows the branch of, one space after the branch, grey, each only when it
  isn't 0:
  - `±N`: the entries `git status --porcelain` lists, so a file staged and changed again counts
    once, and an untracked folder once.
  - `↑N`: the commits on what is checked out that aren't on its upstream; without an upstream, or
    with one that is gone, or on a detached HEAD, those not on `origin/HEAD`; with neither, none.
    It counts against what the clone last fetched: nothing is fetched.
- `⇡` and the version installed, without its patch (`⇡ 0.54`), yellow, after PRD visibility's `⧗`
  and `⚑` and before the model, while the session runs an
  older bagheera than Claude Code records as installed for its project, as `doctor` compares them
  (ADR doctor). The session's version is the one its session start ran, even once a later
  session's start points the Status line's link at a newer copy (ADR binary). The Release gives
  every plugin one version, so bagheera's stands for all three.
- The line runs `git` for `±` and `↑` each time it draws, and waits for it at most 150 ms; past
  that, it shows the counts it last got in that folder, or none.
- Where the line doesn't fit, PRD visibility's order holds (the details, then the model); `±N`,
  `↑N` and `⇡` stay. Past that, the folder's name is cut short with `…`.
- ADR status-line and the glossary's Status line are rewritten with the change that builds this,
  with PRD visibility's.

## Non-goals

- Commits behind the upstream (`↓N`): they need a fetch, and without one they mislead.
- A branch not checked out, and another project's uncommitted work.
- The session's cost, lines added and removed, the Output style, Claude Code's version: they
  change no decision, or seldom, and take room every time.

## Anti-goals

- The line draws slower than PRD visibility's budget, or blank, because `git` is slow or fails.

## Acceptance criteria

- In a clone with 2 files changed, one of them staged and changed again, and an untracked folder
  of 3 files, the line shows `±3`; with none, no `±`.
- On a branch 2 commits ahead of its upstream, the line shows `↑2`; on one with no upstream, or
  a detached HEAD, 2 commits past `origin/HEAD`, `↑2`; with neither, no `↑`.
- A session that started on 0.51.1 shows `⇡ 0.52` once 0.52.0 is installed for its project and another
  session has started on 0.52.0; a session that started on 0.52.0 doesn't.
- With `git` made to take 1 s, the line draws within 300 ms, with the counts from the draw before,
  or with none on the first.
- Drawing the line opens no socket and runs no `git fetch`, checked by a test that fails any.
- In 120 columns, in `claude-plugins` on `main` with `±`, `↑`, `⇡` and PRD visibility's `⧗` and
  `⚑`, the line shows all of them, every number with its details, and the model.
- In a line too narrow for all of it, `±N`, `↑N` and `⇡` stay while the details and the model go.
- Outside a repo, the line shows no `±` and no `↑`.
- `±N` and `↑N` are grey, as work in progress is, and `⇡` is yellow.
- In this repo, the whole line, with PRD visibility's part, draws in under 300 ms on the
  maintainer's machine, checked by hand.
