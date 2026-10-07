## Guidelines for more stacks

2026-10-03 · user · kept 2026-10-03

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. Settled by deciding
which stacks get one, each with its stack detection for a new Config, or none. Kept to write
each when a project in that stack takes up baloo.

## Guidelines for concerns across stacks

2026-10-03 · user · kept 2026-10-03

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as Guidelines. Settled by deciding which earn a Guideline
of their own rather than rules in `principles` or `design`, and whether a new Config turns them on.
`principles` already asks that a change be observable in production, and the Checks keep Secrets
out of commits and Claude's context; kept until a session shows a gap they leave.

## Where each kind of project knowledge lives

2026-10-05 · user

A project can keep part of its knowledge outside the repo, in a tool such as Jira, Confluence,
GitHub Issues or a wiki. Agreed so far: the project names where each kind lives (requirements, bugs,
tasks, decisions, test plans, the glossary), and a skill writes there through its connector or
command-line client, else to `.about/`, as ADR issues and ADR prd already do for two kinds;
technical ADRs stay with the code, apart from the project's decisions; what a Session review finds
for a kind kept in an outside tool goes to the local Inbox, for a person to move. To weigh:
Sancrisoft's risk register handed from spec to QA, Squad's opportunity solution tree, Kiro's
steering split into product, tech and structure. Settled once a project keeps a kind in an outside
tool, or `.about/` takes a new kind such as "Records of solved problems": then decide where the map
of kinds to places lives and how a skill finds it, and rewrite ADR about-folder.

## Session start knows every part of the plugin

2026-10-04 · plugin review · kept 2026-10-04

`sessionStart` in `src/baloo/cmd/baloo/main.go`, about 100 lines, calls each part in turn
(Config, Output style, attribution, Status line, Git hooks, Session review, Inbox, Guidelines)
and writes each one's lines for Claude itself; the Inbox's parsing, `inboxItems`, lives there
too, with no package of its own. So a new part edits `main.go` and `main_test.go` (857 lines).
Settled by deciding whether each package returns its own report lines and `main` only gathers
them, with the Inbox's parsing moved to a package of its own, or the orchestration stays as is.
Kept to decide when the next part joins session start.

## Project knowledge reaches the context only as a task needs it

2026-10-06 · user

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

## Records of solved problems

2026-10-07 · session review

Compound Engineering keeps a record of each solved problem in `docs/solutions/`, for a later
session to find; `.about/` has no such kind. Its cost to the context is in "Project knowledge
reaches the context only as a task needs it". Settled by deciding whether baloo takes it.

## No evals for the skills

2026-10-07 · session review

Nothing in the repo measures whether the skills, the agent and the Guidelines make Claude follow
their rules: the Go tests cover the binary, not the prompts, so a change to a skill's text can
weaken it unseen. Settled by deciding whether skills get evals, a set of tasks run against a skill
with its result checked, and which skills first, or that sessions and `retro` are enough. The
measurement of 2026-10-07 (ADR measurement) read sessions, not prompts: it shows whether a part was
used, not whether a skill's text works.

## Interactive sessions leave `.about/` edits nobody reviewed too

2026-10-07 · user

Of 9 edits to `.about/` found uncommitted and unread on 2026-10-07, 5 came from the user's own
interactive sessions, not from a Session review: an interview's results written and never
committed. Proposals cover only the review (ADR session-review). Settled by deciding whether an
interactive session's edits to `.about/` need a step of their own, such as session start naming
uncommitted changes there, or are the user's to commit like any other.
