## Guidelines for more stacks

2026-10-03 · user · kept 2026-11-22

Guidelines beside `go`, `python`, `typescript` and `vue` for `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible). From 2026-11-09 they
are louie's (ADR plugin): each is a file whose `paths:` say which files bring it, so no stack is
detected for a Config. Settled by deciding which stacks get one, or none. Kept to write each when
a project in that stack takes up the plugins; `python`, this repo's stack (ADR binary), shipped in
0.71.0 on 2026-11-21. `docker` gets none: on 2026-11-22 its four eval cases (not as root, `.env`
and `.git` kept out of the build context, Compose without `version:`, a Secret as a build mount)
scored 1.00 without louie on the default model and Claude Sonnet, 3 runs an arm (ADR evals).

## Eval cases for verify, doctor, retro, new and setup

2026-11-01 · evals · kept 2026-11-22

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
Settled by a sandbox that runs Git hooks, lets a skill read the session's Transcript, and lets a
script write `.claude/settings.json` and a folder outside any git repo, or by dropping these cases; each is kept only once it fails without the plugin (ADR evals). From
2026-11-09 `verify` becomes a louie Workflow and `doctor` and `retro` bagheera's (ADR plugin), so
each case moves with its part, in the PRD of that move. On 2026-11-12 none of the three is in
`evals/`, having only been run by hand (`evals/verify/offer` is another case, the offer of a
Verification), and on Claude Code 2.1.322 a run granted `Bash(git *)` still refuses to start while
`~/.docker/contexts` holds a link, even with `DOCKER_CONFIG` set to an empty folder.
On 2026-11-22, on 2.1.330, moving `~/.docker/contexts` alone out of `~/.docker` for the run was
enough to grant `Bash`. `new`'s and `setup`'s cases were written and run with the plugin, and
neither can pass in the sandbox, so neither was kept:
- `new` (a Go and Vue product in `./acme-shop`): the sandbox's home folder, which holds the run's
  folder, is a git repo, so louie's `new` refuses to write inside it, even with the workspace's own
  `.git` removed.
- `setup` (the shop set up without hathi): the sandbox denies the plugin's script a write to
  `.claude/settings.json` (`Read-only file system`), so setup stops having written nothing.
`assess` was kept (case `evals/assess/checks`) though it reads no Transcript there either, as
`retro`: it pins the report being run instead of a guess.

## A commit's body says why

2026-11-08 · Missing Semester 2026, Beyond the Code · kept 2026-11-22

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

2026-11-18 · user, from a post on nine personal agents · kept 2026-11-22

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

2026-11-18 · user, from a post on a smart home that grows its own controls · kept 2026-11-22

The post's system watches how a device is used and comes with one apt question. The Assessment
watches, but says nothing until asked, by its Non-goal "Showing anything in the Status line or at
session start" (PRD assessment). Its report of 2026-11-18 had such figures: `no-git-hook-bypass`
4 of 4 denials false, `baloo:architecture` loaded once in 30 days, `go`, `typescript` and `vue`
before the first edit of their files 0 of 13, 0 of 9 and 0 of 5. Settled by deciding the lines
(a Check's denials mostly false, a part unused for 30 days) and where the question goes, such as
a Proposal to this repo's Inbox; or by keeping the report asked for.

A post of 2026-11-25 (habr.com/ru/articles/1112164, Agentic Playbooks) gives such lines for its
own learned rules: a rule only after three alike signals, then a trial; quarantined while its
violations are at least its applications; retired after 90 days unapplied. They would fit a
Guideline or a Check here: `no-git-hook-bypass` at 4 of 4 false is past the quarantine line.

## A Proposal kind that has earned it applies itself

2026-11-18 · user, from a post on a smart home that grows its own controls · kept 2026-11-22

The post's devices climb a ladder of trust: watch, suggest, act on a command, act alone on agreed
scenarios, each step up only by the person's leave, and a dangerous one only switched off. The
Session review stands at suggest: every Proposal waits for the user (ADR measurement, after it
wrote into `.about/` unasked). A kind the user accepted every time, such as a glossary edit
accepted 10 times of 10, might with the user's yes apply itself and say so. On 2026-11-18 the
log held 11 accepted and 3 rejected in 30 days, across every kind. On 2026-11-22, across every
repo on the machine over 30 days: `adr edit` accepted unedited 12 of 13, `glossary edit` 6 of 7,
`inbox add` 39 of 46 (5 rejected); the user kept every Proposal asked, the samples being small.
Settled by the Session review's log showing a kind accepted unedited often enough to trust, and
the user's yes; or by keeping every Proposal asked.

## The implementer's rebase cites a Guideline its context doesn't name

2026-11-22 · session on tests in `/louie:implement`

`agents/implementer.md`'s `rebase` stage resolves conflicts "as the `principles.md` Guideline your
context names says", but a Workflow's agent starts with no `SubagentStart` and so no Guidelines
index (ADR verify), and the Hook gives the index to the verifier alone; PRD implement's Scope says
each stage is given it. Settled by the stage reading `principles.md` from louie's folder as the
implement stage now reads `testing.md`, or the PRD dropping the index for the other agents.

## Checking a PRD's Success signal after its Release

2026-11-22 · user

Most PRDs name a Success signal with a window ("in the first 30 days after the Release"), but
nothing reminds anyone to check it once the window ends: the Assessment counts how the plugins do,
not whether a project's feature met its PRD. The rest of the cycle after a merge (deploy, CI,
monitoring) stays the project's and the person's (PRD harness, Anti-goals; PRD hand-back), so this
is the one gap worth closing. Settled by deciding whether, and where, a reminder is left: e.g. an
Inbox item `/louie:merge` writes when it merges a change serving a PRD, dated for the window's
end, or `/baloo:prd` checking signals whose window has passed; or by deciding not to.

## A Verification that checked nothing passes

2026-11-27 · user, from a post on agents' playbooks (habr.com/ru/articles/1112164)

The post's point: a check of a report's shape passes an empty one, so a run that found nothing
looks like one that looked and found nothing. `workflows/verify.js` is so: a verifier that returns
no departures and an empty `criteria` gives `Verdict: pass`, with "none found for this change"
under the criteria, even when a Ticket or PRD with criteria was named; and the schema has no
field for what each source checked (verifier.md asks for it in a line, the schema drops it).
Settled by the script failing, or saying not checked, when the criteria source returns no
criterion for a target that has them, and a `checked` field each verifier fills (the ADRs, terms
or Guidelines it read); or by deciding the pass with nothing found is right.

## louie's agents can't read a Ticket kept in a tracker reached only by a connector

2026-11-27 · user, while settling PRD code-host

`louie:planner`, `louie:implementer` and `louie:verifier` name only `Read, Grep, Glob, Bash` in
their `tools:`, and an agent with that list gets no MCP tool, so a Workflow's stage reads a
tracker's Ticket only through a command-line client in Bash (`gh issue view`, `jira`). A project
whose tracker is reached only by a connector (Atlassian's, say) gets no Ticket in `/louie:plan`,
`/louie:implement` or `/louie:verify`; a company project's subagents read Jira only because its own
agents name the Jira server's tools. Not checked in a run. Settled by a run on a Jira Ticket with
no `jira` client, and, if it fails, by the skill that starts the Workflow reading the Ticket in the
main session, which has the connectors, and handing its text to the Workflow; where Tickets are
kept stays as ADR tickets has it.
