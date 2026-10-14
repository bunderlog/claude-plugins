## Guidelines for more stacks

2026-10-03 · user · kept 2026-10-14

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. Settled by deciding
which stacks get one, each with its stack detection for a new Config, or none. Kept to write
each when a project in that stack takes up baloo: `python` when the port to Python starts (ADR
binary), since this repo becomes that project.

## Guidelines for concerns across stacks

2026-10-03 · user · kept 2026-10-14

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as Guidelines. Settled by deciding which earn a Guideline
of their own rather than rules in `principles` or `design`, and whether a new Config turns them on.
`principles` already asks that a change be observable in production, and the Checks keep Secrets
out of commits and Claude's context; kept until a session shows a gap they leave.

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
a skill finds it, and rewrite ADR about-folder.

## Project knowledge reaches the context only as a task needs it

2026-10-06 · user · kept 2026-10-14

After a few weeks, this repo's `.about/` is about 25k tokens (20 ADRs about 82 KB, the glossary
and the Inbox about 15 KB) and the Guidelines another 10k, and both only grow; the more of it a
session holds, the worse Claude follows what matters. Today session start prints a line per
Guideline and the Inbox's count, and the skills and the verifier pick ADRs by the subject in their
file names; ADRs and PRDs are edited in place, so nothing superseded piles up in the files.
Measures to weigh:

- Session start lists the titles of the ADRs, terms and PRDs, and Claude reads a file by its path.
- The binary picks what a task needs from the files it touches, once ADRs and acceptance criteria
  link to code.
- Reading many ADRs goes to an agent of its own, as the verifier does, which returns only its
  report.
- The binary counts the tokens session start adds and says when they pass a budget.
- A kind that only grows, such as Compound Engineering's `docs/solutions/` of solved problems,
  gets a search and a cleanup before baloo adds it, and what it archives stays out of every
  listing.

Settled by measuring how much of `.about/` a session holds in a project a year old, then deciding
which measures earn their cost.

Loading on a task's demand is itself an open question, not a confirmed approach: the measurement
of 2026-10-07 found the Guidelines read before an edit on their subject in 5 of 79 cases, and
`.about/` read before an edit to code in 8 of 28 sessions.

## Guidelines tied to a task, not a file, still wait to be read

2026-10-07 · user · kept 2026-10-14

`debugging`, `ci`, `design`, `principles`, `writing-for-agents` and `dependencies` reach Claude
only as a line of session start's index, for Claude to read when their task comes up; the
measurement of 2026-10-07 found a Guideline read before an edit on its subject in 5 of 79 cases,
and in one project in 0 of 29 (ADR measurement). The file Claude touches can't tell their task,
so the Hook that gives `typescript`, `vue` and `testing` (ADR guidelines) doesn't reach them.
Settled by finding a signal that does tell the task, such as a failing test run for `debugging`
or a CI run named in the prompt for `ci`, or deciding they stay Claude's to read.
Kept to settle with the port to Python (ADR binary), which rewrites the Hooks anyway; an eval
suite (ADR evals) can measure whether a signal makes Claude read them.

## The Release workflow's runner moves to Ubuntu 26

2026-10-06 · session review · kept 2026-10-14

The `ubuntu-latest` label that CI and the Release workflow run on moves to Ubuntu 26 from
2026-10-19; the v0.21.1 Release run warned of it. Settled by pinning the runner, or by seeing a
run on Ubuntu 26 pass after 2026-10-19.

## A plugin for another audience, such as ad managers

2026-10-14 · user

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
