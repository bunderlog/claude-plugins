## Guidelines for more stacks

2026-10-03 · user · kept 2026-11-12

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. From 2026-11-09 they
are louie's (ADR plugin): each is a file whose `paths:` say which files bring it, so no stack is
detected for a Config. Settled by deciding which stacks get one, or none. Kept to write each when
a project in that stack takes up the plugins; `python`, this repo's stack from 0.26.0 (ADR
binary), waits until a measurement shows the Guidelines a Hook gives from 0.27.0 are followed.

## A plugin for another audience, such as ad managers

2026-10-14 · user · kept 2026-11-12

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

2026-11-01 · evals · kept 2026-11-12

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
`evals/`, having only been run by hand; `evals/verify/offer` is another case, the offer of a
Verification.

## A commit's body says why

2026-11-08 · Missing Semester 2026, Beyond the Code · kept 2026-11-12

The lecture asks a commit's body for what forced the change, the alternatives weighed, the
trade-offs and what may surprise, at a length that grows with the change: a subject alone for a
typo, Problem → Solution → Implications for a subtle fix; an LLM writes it in the session that
made the change, and asks the user for what it doesn't know. baloo checks only a commit's format
(`conventional-commits`) and says nothing of a body. Its half on comments became a line in
`principles` on 2026-11-12 (case `evals/principles/why-comment`); a case for a body needs the
agent to commit, with Bash, which the sandbox doesn't run yet (see the item on verify's cases).
Settled by an eval case where Claude writes a body that only restates the diff, failing without
the rule and passing with it (ADR evals): then lines in `principles`; or by dropping the idea.

## `deliver` re-plans and stops on a decision the earlier plan didn't raise

2026-11-10 · session · kept 2026-11-12

`/louie:deliver` runs `louie:plan` afresh, so each run's plan can find a decision the plan before
it didn't: Issue louie-new-scaffold stopped on the `.tmpl` storage after `/louie:plan` raised only
what `mise run check` runs, and Issue louie-new-api on whether the server opens a database after
`/louie:plan` raised only the example migration. Each stop costs a planner run and a decision
comment, and the user said to stop only when it is truly unclear. Settled by deciding whether
`deliver` takes a plan already made (its report, with the decisions written into the Issue), or
whether the planner treats a choice with a recommended option that no criterion or ADR rules out
as an assumption rather than a decision. `deliver` on several Issues plans them all before
building any and lists every decision in one report (PRD batch), which leaves only `/louie:plan`'s
own plan going unused. Waiting costs little for now: the Assessment of
2026-11-12 counted no session that loaded `deliver` or `plan` in 30 days.

## Does the index get the ADR or PRD read before an edit?

2026-11-12 · assessment · kept 2026-11-12

PRD index's success signal: of the edits to a file an ADR or PRD names, more than half come after
a read of it, and above 0 in webui. Before the index (0.52.0, 2026-11-10) it was 9 of 65 code
edits in 30 days, webui 0 of 23; on 2026-11-12 there were only 3 since, 1 after a read.
Settled by counting a month after the Release, from 2026-12-10, with `/bagheera:assess`: keep the
index if it moved past half, otherwise change how it asks or drop the rule (ADR measurement).
