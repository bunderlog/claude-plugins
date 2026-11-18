## Guidelines for more stacks

2026-10-03 · user · kept 2026-11-16

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. From 2026-11-09 they
are louie's (ADR plugin): each is a file whose `paths:` say which files bring it, so no stack is
detected for a Config. Settled by deciding which stacks get one, or none. Kept to write each when
a project in that stack takes up the plugins; `python`, this repo's stack from 0.26.0 (ADR
binary), waits until a measurement shows the Guidelines a Hook gives from 0.27.0 are followed.

## A plugin for another audience, such as ad managers

2026-10-14 · user · kept 2026-11-16

baloo split into smaller plugins, so a role installs only what it needs, was weighed again on
2026-10-14 for installing by choice and different audiences, and not done: no such user exists
yet. The split of 2026-11-09 into baloo, louie and bagheera (ADR plugin) is by who turns a part
on, not by audience, so this stays open; the survey below on tags and shared code serves the
Release tool for several plugins either way. The first candidates are ad managers, two ways:
- moved to Claude Code, working in a git clone: ADR about-folder holds, baloo with its Hooks works
  for them as it is, and what they lack is skills of their own domain, a plugin beside baloo or
  skills in it;
- left in Cowork or claude.ai, with no git or terminal, which ADR about-folder rules out for
  baloo: a plugin of their own, skills only and no Hooks, with their knowledge outside `.about/`.

Which way turns on what they need more: their daily work (reports, creatives, campaigns through
connectors) fits Cowork, with a plugin of skills only; knowledge the team builds and checks
together (a glossary, decisions, playbooks, with history and review) fits Claude Code's desktop
app, with Claude making the commits, and a repo of knowledge alone, since they have no code. To
try first: one ad manager on a real task for a week in Claude Code's desktop app; where git gets in
the way and `.about/` goes unused, it is Cowork.

`.about/` reached from Cowork through an MCP server that writes to GitHub, weighed 2026-10-14:
they would need no git, and each change would still be a commit or a PR, with its history. It
doesn't bring baloo: its skills read and edit `.about/` as local files, so each would need
rewriting for the server's tools; Hooks in Cowork are unreliable and no session's end runs a
Session review; someone has to review the PRs, or changes land on `main` unread; and a token that
writes to the repo lives in Cowork's connector. Whether Cowork has a GitHub connector that writes
is unchecked. ADR about-folder rejected such a server because every role works in a clone, which
ad managers in Cowork wouldn't. Worth building only if they stay in Cowork, as their own plugin of
skills for the server, not as baloo.

The port to Python (ADR binary) makes a second plugin cheap: no binaries to build per plugin.
Settled once a first real ad manager has a task for it: then decide which way, what repo they
clone if any, the plugin's skills, the repo's layout for two plugins, and rewrite ADR plugin, and
ADR about-folder for the second way.

Found in a survey of plugin repos on 2026-10-14, for that layout:
- One owner's plugins live in one repo under `plugins/<name>/`, by relative path (anthropics/
  claude-code, trailofbits/skills, wshobson/agents); obra/superpowers alone keeps a repo each.
  superpowers split its skills out and merged them back, and compound-engineering went from
  several plugins to one (PR #967); wshobson's fine split left 7 differing copies of one agent.
- Claude Code resolves a plugin's `dependencies`, semver ranges, against tags
  `<plugin>--v<version>` (`claude plugin tag --push`), so a second plugin means those tags, not
  `v*`; a plugin with only `dependencies` is a bundle, so baloo could become one over smaller
  plugins. No surveyed marketplace uses `dependencies` yet, `update` doesn't resolve new ones
  (anthropics/claude-code #88663), and `claude plugin eval` loads no dependency.
- An installed plugin is copied to a cache, so `../shared` isn't found, but a symlink to elsewhere
  in the marketplace becomes a copy: shared Python code can live once and be linked into each.

## Eval cases for verify, doctor and retro

2026-11-01 · evals · kept 2026-11-16

Their cases need Bash (the verifier reads the diff through git, doctor and retro run the plugin's
scripts). On 2026-11-02 Bash was granted by moving every link out of `~/.docker` for the run
(`contexts` and `features.json`, both Docker Desktop's WSL links; moving them within `~/.docker`
isn't enough) and back after it, with `--allow-tools 'Bash(git *)' 'Bash(python3 *)'
'Bash(CLAUDE_PLUGIN_DATA=*)'`. What the runs then showed:
- The sandbox can't read the home folder, so a `python3` installed there (mise's) fails to start;
  a run needs `PATH=/usr/bin:/bin` and `claude` by its full path, for the system's python3.
- The harness runs git with `core.hooksPath=/dev/null`, so no Git hook runs in a case and doctor's
  case of the team's `commit-msg` hook is about the harness, not the plugin: 0.67 with and 0.67
  without on Opus, 0.00 both ways on Sonnet, most replies naming `/dev/null`.
- `verify`'s case (`cancel_purchase` where the glossary avoids "purchase", a criterion without a
  test) found the word without the plugin too, and its judge split on the same reply: 0.67 with,
  0.33 without on Opus; 0.67 with, 0.00 without on Sonnet. Some of the verifier's git calls were
  denied.
- `retro` reads Transcripts from Claude Code's config, which the sandbox hides; a case for it can't
  run under `claude plugin eval` as it is.
Settled by a sandbox that runs Git hooks and lets a skill read the session's Transcript, or by
dropping these cases; each is kept only once it fails without the plugin (ADR evals). From
2026-11-09 `verify` becomes a louie Workflow and `doctor` and `retro` bagheera's (ADR plugin), so
each case moves with its part, in the PRD of that move. On 2026-11-12 none of the three is in
`evals/`, having only been run by hand (`evals/verify/offer` is another case, the offer of a
Verification), and on Claude Code 2.1.322 a run granted `Bash(git *)` still refuses to start while
`~/.docker/contexts` holds a link, even with `DOCKER_CONFIG` set to an empty folder.

## A commit's body says why

2026-11-08 · Missing Semester 2026, Beyond the Code · kept 2026-11-16

The lecture asks a commit's body for what forced the change, the alternatives weighed, the
trade-offs and what may surprise, at a length that grows with the change: a subject alone for a
typo, Problem → Solution → Implications for a subtle fix; an LLM writes it in the session that
made the change, and asks the user for what it doesn't know. `hathi` checks only a commit's
format (`conventional-commits`) and nothing says what its body holds. Its half on comments became
a line in `principles` on 2026-11-12 (case `evals/principles/why-comment`); a case for a body
needs the agent to commit, with Bash, which the sandbox doesn't run yet (see the item on verify's
cases).
Settled by an eval case where Claude writes a body that only restates the diff, failing without
the rule and passing with it (ADR evals): then lines in `principles`; or by dropping the idea.

## A Guideline that names the discipline it rests on

2026-11-18 · user, from a post on nine personal agents · kept 2026-11-18

The post's agents work well once each is given a recognised method to follow (a textbook, a
standard, a book such as Nygard's *Release It!*), not rules written from scratch. louie's
Guidelines cite no source. A model knows such books, so naming one may stand in for paragraphs of
rules and shorten what every session reads: `debugging` on Agans' *Debugging: The 9
Indispensable Rules*, `design` and the `architecture` skill on Ousterhout's *A Philosophy of
Software Design*, whose deep modules they already follow, `ci` on *Release It!*. Settled by an
eval of one Guideline, rewritten to name its source and cut what that source already says,
scoring as well as the current text (ADR evals): then the same for the others; or by dropping the
idea.

## The Assessment asks about a figure that crosses a line

2026-11-18 · user, from a post on a smart home that grows its own controls · kept 2026-11-18

The post's system watches how a device is used and comes with one apt question. The Assessment
watches, but says nothing until asked, by its Non-goal "Showing anything in the Status line or at
session start" (PRD assessment). Its report of 2026-11-18 had such figures: `no-git-hook-bypass`
4 of 4 denials false, `baloo:architecture` loaded once in 30 days, `go`, `typescript` and `vue`
before the first edit of their files 0 of 13, 0 of 9 and 0 of 5. Settled by deciding the lines
(a Check's denials mostly false, a part unused for 30 days) and where the question goes, such as
a Proposal to this repo's Inbox; or by keeping the report asked for.

## A Proposal kind that has earned it applies itself

2026-11-18 · user, from a post on a smart home that grows its own controls · kept 2026-11-18

The post's devices climb a ladder of trust: watch, suggest, act on a command, act alone on agreed
scenarios, each step up only by the person's leave, and a dangerous one only switched off. The
Session review stands at suggest: every Proposal waits for the user (ADR measurement, after it
wrote into `.about/` unasked). A kind the user accepted every time, such as a glossary edit
accepted 10 times of 10, might with the user's yes apply itself and say so. On 2026-11-18 the
log held 11 accepted and 3 rejected in 30 days, across every kind. Settled by the Session
review's log showing a kind accepted unedited often enough to trust, and the user's yes; or by
keeping every Proposal asked.

## The pull request stage as an agent of its own, kept from what implement may run

2026-11-18 · user · kept 2026-11-18

`louie:implementer` runs every writing stage of `implement` (prepare, implement, rework, pull
request, discard), though they need different commands: implement runs the checks, `git add`,
`git commit` and `git diff`; the pull request stage only `git push` and `gh pr create`. An agent's
`tools` can't tell one Bash command from another, so a separate agent for the pull request alone
would lose only Edit and Write, and could still change and commit through Bash. The script's
check that the pushed head is the commit the Verification passed is in PRD implement since
2026-11-18. Left:
- a pull request agent of its own;
- a PreToolUse Hook that allows each agent only its commands: no `git push` for the implementer,
  nothing but `git push` and `gh pr` for the pull request's agent. It needs Claude Code to name
  the agent in PreToolUse's input, to check first; louie tells agents apart only at
  SubagentStart now.
Settled by deciding them in PRD implement, once the Hook is known to be possible.
