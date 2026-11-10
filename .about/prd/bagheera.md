# bagheera keeps each person's sessions safe and shows what they leave behind

## Problem

baloo carries both the project's method and each person's session machinery, so a person can't
have the second everywhere without the first, and the project can't turn its method on without
imposing the machinery (PRD harness, ADR plugin).

## Users

- Each person who works with Claude Code: they install bagheera once, and it works in every
  session, the home folder included.
- Not for: a project that wants the same for everyone; it can't turn bagheera on for its team.

## Success signal

In a session with bagheera and without baloo, a `cat .env` is refused, and the Status line the
person set from bagheera's command draws.

## Scope

- bagheera, a plugin of the `bunderlog` marketplace, released with the others under one version,
  takes from baloo: the Checks in Hooks, the Status line's command, `doctor`, the Session review
  with its Proposals, the Retro and the Transcripts' condenser, and the `short-replies` Output
  style; and session start's telling, once per clone, how the person sets their own Output style
  and Status line.
- It shares no code with baloo: the helpers both need are copied. It reads baloo's files only where
  a Session review loads the `glossary` and `adr` skills, from baloo's folder beside its own.
- Proposals are bagheera's end to end: a session start or prompt shows every one waiting, those for
  the Inbox too, and bagheera logs each decision; the `inbox` skill goes through the Inbox only.
- baloo keeps, until louie takes them, its skills but `retro` and `doctor`, the verifier, the
  Guidelines given by a task's signal, and session start's Inbox count, uncommitted `.about/`
  files and index of Guidelines; it keeps letting an old Git hook it wrote through.
- A Release says once that bagheera is to be installed (`claude plugin install bagheera@bunderlog`)
  and `bagheera:short-replies` picked in place of `baloo:short-replies`.

## Non-goals

- Setting a project up, and bagheera's `doctor` over the machine's projects: PRDs of their own.
- louie: Issue split-bagheera-louie.

## Anti-goals

- A Check that guarded a session before stops guarding it, for a person who installs bagheera.

## Acceptance criteria

- With bagheera installed and baloo off, in a repo, Claude's `cat .env` and `git commit
  --no-verify` are refused, and `doctor` runs; with baloo on and bagheera off, neither is refused.
- bagheera's and baloo's `plugin.json` carry the same version at each Release tag.
- A session's end with bagheera on starts a Session review, which loads baloo's `glossary` and
  `adr` skills from the folder beside bagheera's.
- The tests of each plugin's code run with the other's folder gone.
