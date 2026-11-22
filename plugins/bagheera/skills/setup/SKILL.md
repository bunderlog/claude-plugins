---
name: setup
description: Set the current repo up for bunderlog's plugins in one step, and complete the machine's other projects that lack an item — when the user asks to set a project up, turn baloo and louie on in it, or when session start or doctor says a repo isn't set up. Writes the committed Setup (settings, CLAUDE.md, Git hooks running hathi, .gitignore, the ADR), removes what an earlier baloo left, installs hathi with mise, installs or updates the plugins the repo turns on, and turns the clone's Git hooks on; the user reads each diff and commits. Not for installing mise, or for starting a repo that isn't set up at all from another project's session.
---

# Setup

The plugin's script does everything mechanical: it writes the files, installs `hathi` with mise
where it is missing or old, installs or updates the plugins the repo turns on, and turns this
clone's Git hooks on, its only change to git's config being `core.hooksPath`. You ask one
question, write the ADR, and report. Commit nothing: that is the user's. After this repo, you
offer the machine's other projects that need what a run does, and do the same in each the user
picks.

## Run

1. If the repo has no `.hathi.yml`, ask the user whether to add `hathi`, the commit Checks its
   Git hooks run (recommended: yes). Where the repo already checks Secrets in a hook of its own,
   say so in the question.
2. From the project folder, run
   `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --hathi` on yes, `--no-hathi` on
   no, and no flag where `.hathi.yml` is there.
3. Exit 1 with nothing on stdout means it wrote nothing; its `bagheera setup:` line on stderr
   says why and what the user does, such as installing `hathi` with mise. Where it names a
   command for the user, such as mise's installer or the link to mise's shims, offer it to them
   at once, to run as `! <command>` in the prompt, and run setup again once they have; installing
   mise stays theirs. Otherwise keep that line for the report, skip the ADR, and go on: the
   machine's other projects don't depend on this repo's run.
4. Otherwise it prints what it `changed:` and `removed:`, the commands it `ran:` (a plugin
   installed or updated, the Git hooks turned on), each command that `failed:` with its error,
   and what is `left:`. Exit 1 with `failed:` means every other item was written: write the ADR
   as below, and keep each failed command and its error for the report.

## The ADR

Where `left:` asks for `.about/adr/repo-setup.md`, write it in the form the project's other ADRs
use (the `adr` skill's, if baloo is on): its title the decision, such as "This repo is set up as
any project is: its Git hooks in `.githooks/` run `hathi`"; a `Date:` line of today; then whether
the repo runs `hathi`, what checks Secrets in its commits, and what an earlier baloo left that the
run removed, from its `removed:` lines. Write only what the run and the repo show.

## The machine's other projects

Then run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --others`, whatever this
repo's run did. It prints each of the machine's projects that turns baloo on and still lacks an
item, has a plugin to install or update, or has its Git hooks off, with what it `needs` and
whether it has `.hathi.yml`. Do this every time: the user can't see those projects from here.

1. With `no other project to complete`, skip to Report.
2. Otherwise ask the user which to complete: one AskUserQuestion question, `multiSelect: true`,
   an option per project naming its folder and what it needs. Picking none is an answer, and ends
   this section.
3. Then, for the projects picked that have no `.hathi.yml`, ask whether to add `hathi` there
   (recommended: yes), one question each, four to a round until every one of them is answered.
4. For each project picked, run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' setup --in
   <its folder>`, with `--hathi` or `--no-hathi` where it had no `.hathi.yml`, and write its ADR
   as above, in that project. Exit 1 reads as in this repo: with nothing on stdout it wrote
   nothing there, so keep its `bagheera setup:` line for the report and go on to the next
   project; with `failed:`, every other item was written, so write its ADR and keep each failed
   command. Every project picked is run or has a line.

## Report

Then run `python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' doctor`, and tell the user in a few
lines: what changed and what was removed, what it ran (each plugin installed or updated loads from
the next session, not this one), each command that failed with its error, any item doctor still
names missing, and that committing the diff is theirs.

Where you completed other projects, add a line each: what you wrote and ran there, each command
that failed, and that its commit is the user's too; and a line for each project that stopped, with
what stopped it.
