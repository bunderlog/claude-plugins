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

## A plugin per role, with baloo for the knowledge every role shares

2026-10-03 · user

The direction, nothing changed yet: baloo keeps only the project's knowledge, which every role
works with, and each role gets a plugin of its own on top. A role's plugin writes through
baloo's skills rather than its own: `kaa`'s bug report files through `issue`. It reverses ADR
plugin's "new work that leans on baloo is part of baloo", which is what grows baloo's entropy.
The rough split, ★ for what doesn't exist yet:

- baloo, knowledge: `adr`, `glossary`, `prd`, `interview`, `inbox`, `issue`, `verify` and its
  agent, `tidy`, `retro`, `doctor`; the Session review; the rules of `writing-for-agents` and of
  the Inbox, built into its skills rather than through Guidelines.
- `bagheera`, developers: `architecture`; the Guidelines but `writing-for-agents`, with the rules
  on every task and in zsh; the Checks, in Git hooks and in Claude Code's Hooks; the Stop check
  and Format on edit; the binary, its Loader and the CI recipe.
- `kaa`, QA, for testers who see the tracker and the stand: ★ `plan` (a test plan and cases),
  ★ `bug` (filed through `issue`), ★ `explore` (an exploratory session), ★ `regression` (what to
  run and whether to ship; not `release`, which the glossary's Release takes). Manual and
  exploratory testing only; skills only, no Hooks; its work goes to the tracker when the Config
  `.claude/kaa.yml` names one, to markdown files otherwise, a TMS later; a browser only through
  a tool already installed. Later: a log of the browser's actions through `PostToolUse`.
- `akela`, product managers, built once a real PM asks: ★ `discovery` (problems from interviews,
  feedback and tickets), ★ `prioritize` (the backlog against a PRD's goals), ★ `roadmap`,
  ★ `update` (for stakeholders, or release notes from the tracker), ★ `outcome` (whether a PRD's
  measure of success shows); requirements and tasks through `prd` and `issue`.

The repo becomes symmetric, `plugins/<name>/` each with its README and CHANGELOG, tags
`<name>-v*`, with the `v*` tags kept for good, since installed copies of baloo download their
binary by them (`plugins/baloo/scripts/loader`).

Settled by deciding:
- where the knowledge lives for roles without the code repo: read access to it, a repo of
  `.about/` alone, or a store such as Notion through MCP;
- whether every role gets a thin layer of safety and convenience without `bagheera`:
  `no-stale-adr-date`, a Git hook's Check on knowledge; `no-secrets-in-context` and
  `no-destructive-commands`, which guard any role at a terminal; the Output style and the Status
  line, neither knowledge nor a role's. It turns on the first: a tester or a PM in a clone of
  the repo needs the same guard as a developer;
- one binary for baloo and `bagheera`, or one each from a shared Go module;
- how installed copies of baloo learn their Checks and Guidelines moved, with the Config split
  between the plugins.

Then rewrite ADR plugin.
