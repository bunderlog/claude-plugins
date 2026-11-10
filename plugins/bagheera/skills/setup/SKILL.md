---
name: setup
description: Set the current repo up for bunderlog's plugins in one step — when the user asks to set a project up, turn baloo and louie on in it, or when session start or doctor says the repo isn't set up. Writes the committed Setup (settings, CLAUDE.md, Git hooks running hathi, .gitignore, the ADR) and removes what an earlier baloo left; the user reads the diff and commits. Not for installing hathi or mise, or for another repo than the session's.
---

# Setup

The plugin's script writes everything mechanical; you ask one question, write the ADR, and
report. Commit nothing, and change no git config: both are the user's.

## Run

1. If the repo has no `.hathi.yml`, ask the user whether to add `hathi`, the commit Checks its
   Git hooks run (recommended: yes). Where the repo already checks Secrets in a hook of its own,
   say so in the question.
2. From the project folder, run
   `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --hathi` on yes, `--no-hathi` on
   no, and no flag where `.hathi.yml` is there.
3. Exit 1 means it wrote nothing; its `bagheera setup:` line says why and what the user does,
   such as installing `hathi` with mise or brew. Tell them, and stop.
4. Otherwise it prints what it `changed:` and `removed:`, and what is `left:`.

## The ADR

Where `left:` asks for `.about/adr/repo-setup.md`, write it in the form the project's other ADRs
use (the `adr` skill's, if baloo is on): its title the decision, such as "This repo is set up as
any project is: its Git hooks in `.githooks/` run `hathi`"; a `Date:` line of today; then whether
the repo runs `hathi`, what checks Secrets in its commits, and what an earlier baloo left that the
run removed, from its `removed:` lines. Write only what the run and the repo show.

## Report

Then run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' doctor`, and tell the user in a few
lines: what changed and what was removed, any item doctor still names missing, the one command
from `left:` that turns the Git hooks on in this clone (`! <command>` runs it here), and that
committing the diff is theirs. baloo and louie start in the next session once the commit is in.
