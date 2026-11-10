## Guidelines for more stacks

2026-10-03 · user · kept 2026-11-09

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. From 2026-11-09 they
are louie's (ADR plugin): each is a file whose `paths:` say which files bring it, so no stack is
detected for a Config. Settled by deciding which stacks get one, or none. Kept to write each when
a project in that stack takes up the plugins; `python`, this repo's stack from 0.26.0 (ADR
binary), waits until a measurement shows the Guidelines a Hook gives from 0.27.0 are followed.

## Guidelines for concerns across stacks

2026-10-03 · user · kept 2026-11-09

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as baloo's Guidelines. Settled by deciding which earn a
Guideline of their own rather than rules in `principles` or `design`. `principles` already asks
that a change be observable in production, and the Checks keep Secrets out of commits and
Claude's context; kept until a session shows a gap they leave, which a week of three projects in
2026-10 didn't.

## Where each kind of project knowledge lives

2026-10-05 · user · kept 2026-11-09

A project can keep part of its knowledge outside the repo, in a tool such as Jira, Confluence,
GitHub Issues or a wiki. Agreed so far: the project names where each kind lives (requirements, bugs,
tasks, decisions, test plans, the glossary), and a skill writes there through its connector or
command-line client, else to `.about/`, as ADR issues and ADR prd already do for two kinds;
technical ADRs stay with the code, apart from the project's decisions; what a Session review finds
for a kind kept in an outside tool goes to the local Inbox, for a person to move. To weigh:
Sancrisoft's risk register handed from spec to QA, Squad's opportunity solution tree, Kiro's
steering split into product, tech and structure. Settled once a project keeps a kind in an outside
tool, or `.about/` takes a new kind: then decide where the map of kinds to places lives and how
a skill finds it, and rewrite ADR about-folder. One project keeps its tasks and bugs in Jira, and
from 0.26.2 the Session review leaves what is still to do on a ticket to the ticket (ADR
session-review); decide once a skill has to write there, not only read. louie's `deliver` Workflow
will read an Issue from the project's tracker (PRD harness), so its PRD may be where this comes up
first.

## Project knowledge reaches the context only as a task needs it

2026-10-06 · user · kept 2026-11-09

After a few weeks, this repo's `.about/` is about 25k tokens (20 ADRs about 82 KB, the glossary
and the Inbox about 15 KB) and the Guidelines another 10k, and both only grow; the more of it a
session holds, the worse Claude follows what matters. Today session start prints a line per
Guideline and the Inbox's count, and the skills and the verifier pick ADRs by the subject in their
file names; ADRs and PRDs are edited in place, so nothing superseded piles up in the files.
Measures to weigh:

- Session start lists the titles of the ADRs, terms and PRDs, and Claude reads a file by its path.
- The plugin picks what a task needs from the files it touches, once ADRs and acceptance criteria
  link to code.
- Reading many ADRs goes to an agent of its own, as the verifier does, which returns only its
  report.
- The plugin counts the tokens session start adds and says when they pass a budget.
- A kind that only grows, such as Compound Engineering's `docs/solutions/` of solved problems,
  gets a search and a cleanup before baloo adds it, and what it archives stays out of every
  listing.

Settled by measuring how much of `.about/` a session holds in a project a year old, then deciding
which measures earn their cost.

Loading on a task's demand is itself an open question, not a confirmed approach: the measurement
of 2026-10-07 found the Guidelines read before an edit on their subject in 5 of 79 cases, and
`.about/` read before an edit to code in 8 of 28 sessions, and a week of 2026-10 in one project
in 12 of 30. For the Guidelines, 0.27.0 gives each by a signal of its task instead (ADR
guidelines); `.about/` still waits to be read.

The usefulness check of 2026-09-29 to 2026-10-30 found `.about/` read, or named, before an edit to
code in 24 of 71 sessions in webui, though 67 of them had it, against 28 of 29 in three other
projects. Size alone doesn't explain it: webui's ADRs, glossary, Inbox and PRDs are about 118 KB,
64 KB of it the Inbox, and one of the three, read before every edit, has about 87 KB.

What webui's sessions had in common, read on 2026-10-31: of 52 that edited its code, 41 began with
a Jira ticket, and 1 of those 41 read an ADR, the glossary or a PRD before the first edit, against
6 of the other 11. A ticket was named in `.about/` before its session in 3 of 40; 6 of webui's 10
ADRs are about its process, not its code, and most tickets fix a legacy screen that no ADR or PRD
covers. Where one did, Claude read it: RPG-6249, a menu regression, read ADR vue-migration before
its fix and updated it after, and the project's own skills link to ADRs such as
device-capabilities. No webui2 edit compared a device's type outside `entities/deviceConfig/`, the
one rule of an ADR checked. So the count misleads: it judges a session by its first edit, where a
webui session often works through several tickets.

Counted per edit on 2026-11-02, on this machine's sessions from 2026-10-01: of 545 edits to code in
81 sessions in six projects, 52 had an ADR or PRD that names the edited file, or a path of two or
more segments ending in its folder, such as `entities/deviceConfig`, and for 20 of them it was read
earlier in the session or a subagent of it; in webui 0 of 22, in the others 20 of 30. `.about/` was
read at all before 341 of the 545, before 82 of webui's 260. So the ADRs that name code are few, 52
of 545 edits, and in webui none of those reached the edit; an ADR that names no path is missed by
the count, which needs a link from ADRs to code to judge the rest.

On 2026-11-09 PRD harness took the first measure: session start puts the titles of the ADRs and
PRDs and the glossary's terms in the context, derived each time, not kept in a file of their own.
It has a PRD of its own (PRD harness, Non-goals); the measurements above move into it, and this
item goes with them.

## A plugin for another audience, such as ad managers

2026-10-14 · user · kept 2026-11-09

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

2026-11-01 · evals · kept 2026-11-09

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
each case moves with its part, in the PRD of that move.

## A commit's body and a code comment say why

2026-11-08 · Missing Semester 2026, Beyond the Code · kept 2026-11-09

The lecture asks a commit's body for what forced the change, the alternatives weighed, the
trade-offs and what may surprise, at a length that grows with the change: a subject alone for a
typo, Problem → Solution → Implications for a subtle fix; an LLM writes it in the session that
made the change, and asks the user for what it doesn't know. A comment says what the code can't:
why not the obvious way, a choice correctness rests on, where a constant comes from, a TODO with
its reason, a lesson a long debugging taught. baloo checks only a commit's format
(`conventional-commits`) and says nothing of a body or a comment. Settled by an eval case where
Claude writes a body that only restates the diff, or leaves out a why-not comment a later edit
undoes, failing without the rules and passing with them (ADR evals): then a Guideline of its own
or lines in `principles`; or by dropping the idea.

## Property-based tests where no literal can be the expected value

2026-11-08 · Missing Semester 2026, Code Quality · kept 2026-11-09

`testing` §3 takes expected values from outside the code and, where nothing independent exists,
runs the code instead of testing it. A property (a round trip, an invariant, agreement with a
slow reference), checked with Hypothesis or fast-check, is a third way: an independent check
with no literal. Settled by an eval case where Claude restates the code's formula as the
expected value, or leaves logic untested, and the line changes that (ADR evals), or by dropping
the idea.

## `deliver` re-plans and stops on a decision the earlier plan didn't raise

2026-11-10 · session

`/louie:deliver` runs `louie:plan` afresh, so each run's plan can find a decision the plan before
it didn't: Issue louie-new-scaffold stopped on the `.tmpl` storage after `/louie:plan` raised only
what `mise run check` runs, and Issue louie-new-api on whether the server opens a database after
`/louie:plan` raised only the example migration. Each stop costs a planner run and a decision
comment, and the user said to stop only when it is truly unclear. Settled by deciding whether
`deliver` takes a plan already made (its report, with the decisions written into the Issue), or
whether the planner treats a choice with a recommended option that no criterion or ADR rules out
as an assumption rather than a decision.

## What a fresh `go-vue` repo still departs from louie's Guidelines in

2026-11-10 · verify

A verifier run on a repo fresh from `/louie:new` (0.49.0) against louie's Guidelines found one
departure that blocked, fixed in 0.49.1, and these that don't:
- `internal/handler/handler.go`: the `ServeMux` answers an unknown `/api/` path or a wrong method
  with its own plain-text 404 or 405, not `respond`'s JSON (`go` §3); the first to fix once a
  client calls the API.
- `App.vue` and `HomeView.vue` open with no comment, where every `.ts` file does (`typescript`
  §5, which `vue` doesn't ask of a component).
- `CLAUDE.md` restates `mise.toml`'s `setup`, and asks for `mise run check` before a push that
  no hook runs (`writing-for-agents` §2 and §6).
- Smaller: `internal/database` beside sqlc's `internal/db`, two names for one thing (`go` §1); the
  test helper `get` takes no `t` (`go` §4); `main.go` reads its three settings itself, where a
  `config` package comes due as they grow.
Settled by fixing each in the template, or by deciding a rule doesn't reach a template's file.

## The Status line set by hand on a clean machine

2026-11-10 · user

On a clean machine the user set bagheera's Status line by hand (Issue split-bagheera-louie). That
is ADR status-line's rule, since a plugin can't set `statusLine`; whether bagheera writes it into
`~/.claude/settings.json` after the person's yes is PRD harness's open question for the
visibility PRD, and this is the first person who had to do it on their own. Settled in that PRD.
