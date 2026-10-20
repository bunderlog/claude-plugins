## Guidelines for more stacks

2026-10-03 · user · kept 2026-10-14

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. Settled by deciding
which stacks get one, each with its stack detection for a new Config, or none. Kept to write
each when a project in that stack takes up baloo; `python`, this repo's stack from 0.26.0 (ADR
binary), waits until a measurement shows the Guidelines a Hook gives from 0.27.0 are followed.

## Guidelines for concerns across stacks

2026-10-03 · user · kept 2026-10-14

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as Guidelines. Settled by deciding which earn a Guideline
of their own rather than rules in `principles` or `design`, and whether a new Config turns them on.
`principles` already asks that a change be observable in production, and the Checks keep Secrets
out of commits and Claude's context; kept until a session shows a gap they leave, which a week of three projects in 2026-10 didn't.

## Where each kind of project knowledge lives

2026-10-05 · user · kept 2026-10-14

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
session-review); decide once a skill has to write there, not only read.

## Project knowledge reaches the context only as a task needs it

2026-10-06 · user · kept 2026-10-14

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

## The Release workflow's runner moves to Ubuntu 26

2026-10-06 · session review · kept 2026-10-14

The `ubuntu-latest` label that CI and the Release workflow run on moves to Ubuntu 26 from
2026-10-19; the v0.21.1 Release run warned of it. Settled by pinning the runner, or by seeing a
run on Ubuntu 26 pass after 2026-10-19.

## A plugin for another audience, such as ad managers

2026-10-14 · user · kept 2026-10-14

baloo split into smaller plugins, so a role installs only what it needs, was weighed again on
2026-10-14 for installing by choice and different audiences, and not done: no such user exists
yet. The first candidates are ad managers, two ways:
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

## Facts from outside the repo go stale unseen

2026-10-18 · user · kept 2026-10-19

A project's docs and pages quote facts it doesn't own: a competitor's price or free tier, a
vendor's limit, a tool's version. They go stale without any change to the repo, so neither a
review nor `tidy` notices. One project already dates each competitor fact (`asOf` and
`sources` beside it), but nothing ever asks for a recheck. The idea, from the community guide
Claude Code: Everything You Need to Know (an expiry marker per claim checked daily in CI, and a
workflow, `stale-docs-audit.js`, that sorts each claim as stale, unverifiable or ok against its
source): a marker for an outside fact with its check date and
source; session start reporting how many are past due, as it does for the Inbox; and a skill
that rechecks each against its source in a separate agent and proposes the edits. Settled by
choosing the marker's shape, a project-wide recheck interval or one per marker, and whether
the recheck is a skill of its own or part of `tidy`, or by dropping the idea. Kept
until a project asks for its dated facts to be rechecked; on 2026-10-19 one project dated
them and none had asked.

## Session start reports a problem with the Git hooks in every eval run

2026-10-19 · eval

`claude plugin eval` sets `core.hooksPath` to `/dev/null` for each run, so session start puts
`could not write the Git hooks: [Errno 20] Not a directory: '/dev/null/commit-msg'` into the
context of every run with the plugin: a problem nobody there can fix, and text the run without
the plugin doesn't get. Settled by session start treating `/dev/null` as Git hooks turned off and
saying nothing, or by deciding the line is harmless in an eval.

## The adr skill doesn't load on a design proposal

2026-10-20 · adr evals

On 2026-10-20, with the plugin, `adr` loaded in none of the runs of `contradicts-adr`,
`code-contradicts-adr` and `open-question` on Opus or Sonnet, prompts that propose a design
rather than ask to record one; what the plugin adds there comes from the Guidelines, not the
skill. `code-contradicts-adr` also scored 0.00 without the plugin on Sonnet, where it scored
1.00 the day before, so whether it shows anything is unclear. Settled by a `description` that
loads `adr` on these prompts without loading it on any design question (ADR evals rejected that),
then the cases rerun; or by deciding these cases test the Guidelines, and saying so in ADR evals.
