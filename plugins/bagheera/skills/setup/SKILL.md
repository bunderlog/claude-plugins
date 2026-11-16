---
name: setup
description: Set the current repo up for bunderlog's plugins in one step, and complete the machine's other projects that lack an item — when the user asks to set a project up, turn baloo and louie on in it, or when session start or doctor says a repo isn't set up. Writes the committed Setup (settings, CLAUDE.md, Git hooks running hathi, .gitignore, the ADR) and removes what an earlier baloo left; the user reads each diff and commits. Not for installing hathi or mise, or for starting a repo that isn't set up at all from another project's session.
---

# Setup

The plugin's script writes everything mechanical; you ask one question, write the ADR, and
report. Commit nothing, and change no git config: both are the user's. After this repo, you offer
the machine's other projects that lack an item, and do the same in each the user picks.

## Run

1. If the repo has no `.hathi.yml`, ask the user whether to add `hathi`, the commit Checks its
   Git hooks run (recommended: yes). Where the repo already checks Secrets in a hook of its own,
   say so in the question.
2. From the project folder, run
   `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --hathi` on yes, `--no-hathi` on
   no, and no flag where `.hathi.yml` is there.
3. Exit 1 means it wrote nothing; its `bagheera setup:` line says why and what the user does,
   such as installing `hathi` with mise or brew. Keep that line for the report, skip the ADR, and
   go on: the machine's other projects don't depend on this repo's run.
4. Otherwise it prints what it `changed:` and `removed:`, and what is `left:`.

## The ADR

Where `left:` asks for `.about/adr/repo-setup.md`, write it in the form the project's other ADRs
use (the `adr` skill's, if baloo is on): its title the decision, such as "This repo is set up as
any project is: its Git hooks in `.githooks/` run `hathi`"; a `Date:` line of today; then whether
the repo runs `hathi`, what checks Secrets in its commits, and what an earlier baloo left that the
run removed, from its `removed:` lines. Write only what the run and the repo show.

## The machine's other projects

Then run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --others`, whatever this
repo's run did. It prints each of the machine's projects that turns baloo on and still lacks an
item, with what it lacks and whether it has `.hathi.yml`. Do this every time: the user can't see
those projects from here.

1. With `no other project to set up`, skip to Report.
2. Otherwise ask the user which to complete: one AskUserQuestion question, `multiSelect: true`,
   an option per project naming its folder and what it lacks. Picking none is an answer, and ends
   this section.
3. Then, for the projects picked that have no `.hathi.yml`, ask whether to add `hathi` there
   (recommended: yes), one question each, four to a round until every one of them is answered.
4. For each project picked, run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --in
   <its folder>`, with `--hathi` or `--no-hathi` where it had no `.hathi.yml`, and write its ADR
   as above, in that project. Exit 1 means it wrote nothing there: keep its `bagheera setup:` line
   for the report and go on to the next project. Every project picked is run or has a line.

## Report

Then run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' doctor`, and tell the user in a few
lines: what changed and what was removed, any item doctor still names missing, the one command
from `left:` that turns the Git hooks on in this clone (`! <command>` runs it here), and that
committing the diff is theirs. baloo and louie start in the next session once the commit is in.

Where you completed other projects, add a line each: what you wrote there, the command that turns
its Git hooks on, and that its commit is the user's too; and a line for each project that stopped,
with what stopped it.
