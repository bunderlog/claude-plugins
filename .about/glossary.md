# baloo glossary

The plugins of the `bunderlog` marketplace: `baloo`, skills that keep a project's language,
decisions and requirements explicit, write its Issues and go through its Inbox; `louie`,
Guidelines of working rules and a Verification; and `bagheera`, Checks that Hooks trigger, a
Session review, a Retro, an Assessment, an Output style for Claude's replies, a Status line and
`doctor`.

## Distribution

**Release**:
A version of the plugins reaching their users: a tagged commit with the new version in each
`plugin.json` and its section in `CHANGELOG.md`. Installed copies update only to a new Release, so
a change made without one reaches nobody.
_Avoid_: deploy, publish; "Release" for the GitHub Release
_In code_: `src/release/release.py`

**GitHub Release**:
The page on GitHub for a Release's tag, with its `CHANGELOG.md` section as its notes.
_Avoid_: "Release" alone

## The plugins and `hathi`

**bagheera**:
The plugin each person turns on once, for every session: Checks in Hooks beyond Claude Code's
deny rules, the Status line and `doctor`, the Session review, Retro and Assessment, the
`short-replies` Output style, and setting a project up.
_Avoid_: "baloo" for these parts

**louie**:
The plugin a project turns on to build: the Guidelines, each given by its task's signal or named
where it fits, the Verification, and the Workflows from an Issue to a pull request; to come,
templates for a new product (PRD louie, PRD delivery, PRD templates).
_Avoid_: "baloo" for these parts

**`hathi`**:
The Go CLI a project's Git hooks and CI run on each commit: its message format, Secrets, an AI
co-author, linear history and an ADR's Date; it runs without Claude. Its own terms are in its repo.
_Avoid_: hathi as a plugin

**Workflow**:
A Claude Code dynamic workflow: a script a plugin ships that runs many agents, such as
`/louie:verify`; a project turns them on in its `.claude/settings.json`.
_Avoid_: pipeline

**Set up**:
Said of a project whose checked-out commit holds what the PRD setting a project up lists, its
`.claude/settings.json` turning baloo on among it; a clone of it is set up too, its Git hooks
turned on or not.
_Avoid_: installed, which is a plugin's on a machine

## Hooks

**Hook**:
A command Claude Code runs at an event in a session, such as `SessionStart` or `PreToolUse`.
_Avoid_: "hook" for a Git hook; lowercase "hook", but in text for users who don't know these terms
(messages, the README) and in the Guidelines and skills, written for any
project

**Git hook**:
A script git runs at a step of its own (`pre-commit`, `commit-msg`, `pre-push`), on every commit
or push, whether you or Claude made it. A set-up project's own, committed, run `hathi`; no plugin
writes one, and one an earlier baloo wrote lets each commit through (ADR git-hooks).
_Avoid_: "hook" alone

**Check**:
Code in bagheera that a Hook triggers, such as `bagheera:no-secrets-in-context`, always on where
bagheera is (ADR checks); a commit's Checks are `hathi`'s.
_Avoid_: built-in check; "a Check on Claude's tool calls"
_In code_: `bagheera/checks/`

**Guideline**:
A file of working rules louie ships, for any project (`principles`, `design`), for a repo
with a CI (`ci`) or a package manager (`dependencies`), or for one stack (`go`, `vue`), that a Hook
gives Claude by its task's signal, or session start names where it fits the repo (ADR guidelines).
_Avoid_: rule, guide; a skill, which Claude Code always lists; "Guideline" for an Output style
_In code_: `louie/guidelines.py`

**Output style**:
Instructions for how Claude writes its replies, such as `short-replies`, that bagheera ships
and Claude Code sends with every request once a person's own `outputStyle` setting picks one
(ADR output-styles).
_Avoid_: "style" alone; tone

**Status line**:
The line Claude Code shows under the prompt; bagheera's, with the branch and what isn't committed
or pushed, the Usage figures, the Cache figure, the sessions waiting, the projects needing
attention, a restart that runs a newer version and the model, is drawn by bagheera, and set by
each person in their own settings (ADR status-line, PRD visibility, PRD status-line).
_Avoid_: "status" alone, which is a PRD's Status
_In code_: `bagheera/statusline.py`

**Usage figure**:
One of the Status line's three icons and percentages showing how much is used: the context window,
and the 5-hour and 7-day rate limits.
_Avoid_: Usage bar, which it was until 2026-11-11; meter, gauge

**Cache figure**:
The Status line's icon and minutes showing how long the prompt cache stays warm, or that it is
cold, and, without the context, its size: the tokens the next message writes to it again once it
is cold.
_Avoid_: Cache bar, which it was until 2026-11-11; cache meter

## Secrets

**Secret**:
A value that grants access: an API key, token, password or private key. A placeholder, a
published example or a key meant to be public (a Stripe publishable key, a Firebase web key)
isn't one, even where a Check can't tell the difference. An Env file counts as holding Secrets
unless its first line says it holds none.
_Avoid_: credential, key (alone)

**Env file**:
A file of environment settings a program or shell loads: `.env`, `.env.local`, `prod.env`,
direnv's `.envrc`… A template of one (`.env.example`, `.sample`, `.template`, `.dist`) isn't one.

**Leak**:
A Secret reaching anyone or anywhere it wasn't meant for: a commit, Claude's context, another
host.

## Sessions

**Setup**:
Everything that shapes how Claude works in a project: its CLAUDE.md, Claude Code's settings, its
Git hooks, and the skills, Hooks and plugins it uses.
_Avoid_: harness, which is all the projects' Setups and the person's own rules together

**Harness**:
The projects' Setups together with the own rules for Claude (`~/.claude/`) of each person who
works in them, bunderlog's plugins and `hathi`: what keeps work in order across projects and
within a team (PRD harness).
_Avoid_: Setup, which is one project's; environment

**Transcript**:
The record Claude Code keeps of a session: every prompt, reply and tool call, with the call's full
output, so it can hold a Secret a Check missed.
_Avoid_: log, history

**Retro**:
A review the user asks for of how past sessions went: their Stalls, and the change to the Setup
that would have spared each. It looks at how the work went, not at what it produced.
_Avoid_: retrospective, post-mortem
_In code_: the `retro` skill; `bagheera/condense.py`

**Assessment**:
bagheera's count of each session on the machine at its end, and its report from those counts of
how useful each part of bunderlog is and how well it works. It counts names and numbers, never
what the session said.
_Avoid_: measurement, which is a count made by hand (ADR measurement); telemetry
_In code_: the `assess` skill; `bagheera/assess.py`

**Stall**:
A point in a session that cost the user something the Setup could have spared: a failed or
refused tool call, an interrupt, a correction, a prompt the user types again and again. A red test
mid-change, a denial that was right, or a call that is the user's to make each time isn't one.
_Avoid_: issue, incident

**Session review**:
A review bagheera starts itself when a session ends, in every repo: a separate headless session
proposes, as Proposals, what the conversation settled but nobody wrote down, and a later session
asks the user about each. Unlike a Retro, it looks at what was settled, not at how the work went.
_Avoid_: session-end review

**Proposal**:
One change a Session review proposes to the Inbox, the glossary, an ADR or a PRD, with its ready
edit, in `.about/proposals/<review>.md`; it reaches `.about/` only once the user accepts it, and
waits while they defer it; once decided, it is kept in bagheera's data folder. Stale when the
text it changes is gone; a mismatch when the log of decisions and its file disagree.
_Avoid_: suggestion, draft
_In code_: `bagheera/review.py`

**Inbox**:
The file `.about/inbox.md` of what is still to consider: a decision or term still open, a bug or a
finding left for later. An item stays until something settles it, and is then deleted.
_Avoid_: todo, backlog, proposed ADR
_In code_: baloo's `scripts/session-start` counts it; the `inbox` skill goes through it

**Issue**:
Work agreed to do, a bug to fix or a task: a page in the tracker the project names, or else
`.about/issues/<slug>.md`, deleted by the change that does it. Unlike an Inbox item, nothing about
it is still to decide.
_Avoid_: ticket, todo
_In code_: the `issue` skill writes one

**Verification**:
A comparison, which the user asks for or a `deliver` run makes, of a change with what the project
agreed: its ADRs, glossary, the Guidelines that fit the repo, and the acceptance criteria of its
Issue or PRD. louie's agent, the verifier, makes it in a context of its own, so not as the change's
author, one for each source when the `verify` Workflow runs it, and changes nothing. Unlike a code
review, it doesn't hunt bugs; unlike Claude Code's `/verify`, it doesn't run the change; unlike a
Check, it isn't a plugin's code.
_Avoid_: review, already a Session review's, a Retro's and a code review's word
_In code_: the `verify` Workflow; `agents/verifier.md`; `names.VERIFIER`

## Building

**Plan**:
louie's answer for an Issue before it is built: each change, where it goes and the acceptance
criterion it serves, how sure it is, its Open decisions and Assumptions; or nothing to build,
naming the commit that already meets the criteria. Making one changes nothing.
_Avoid_: "plan" for Claude Code's plan mode's, which follows no Issue
_In code_: the `plan` Workflow; `agents/planner.md`

**Open decision**:
A choice only the person can make, which the Issue, the ADRs and the code leave open, such as a
behavior another decision set. A Plan with one stops `deliver` until it is written into the Issue
or an ADR; one found elsewhere waits in the Inbox. Unlike an Assumption, a Plan doesn't take it.
_Avoid_: decision for the person; "decision" alone, which an ADR's is once taken
_In code_: a Plan's `decisions`; the verdict `needs-decision`

**Assumption**:
What a Plan takes as given without asking the person, with what would change if it is wrong: a
way to build it recommends that no criterion, ADR or the Issue rules out, or a question outside
the Issue's criteria that it leaves out. The pull request lists them for review, and one the
review rejects is changed in that pull request: it isn't an Open decision, which stops only a run
not yet building.
_In code_: a Plan's `assumptions`

## Retired terms

- **Config** — `.claude/baloo.yml`, a repo's settings for the plugin, each Check and Guideline
  turned on by a key of its own, until 2026-11-10; Claude Code's settings are the only switch now
  (ADR config).
- **Format on edit** — the plugin's run of the formatter the Config named on each file Claude
  edited, until 2026-11-10; a project's own `PostToolUse` Hook does it now (ADR format-on-edit).

- **Git hook command** — the project's own command, by Git hook under `git-hook-commands` in the
  Config, that the plugin's Git hook ran once its Checks passed, until 2026-11-09; a project's own
  Git hooks run it now (ADR git-hooks).

- **Loader** — the `sh` script that downloaded the plugin's Go binary and ran it, until
  2026-10-14; the Hooks now run `scripts/hook`, which runs the plugin's Python code (ADR binary).
