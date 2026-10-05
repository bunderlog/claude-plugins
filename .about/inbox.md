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

2026-10-03 · user · kept 2026-10-04

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

Agreed since: the terms are one glossary per project, which product, developers and testers
all read and write; a role's plugin keeps no vocabulary of its own and sends a new term to
`glossary`.

Agreed 2026-10-04, changing the split above: baloo can't work without its Hooks, so it keeps
them and a binary (SessionStart gives every task the Inbox's rule and count, SessionEnd runs the
Session review, SubagentStart gives the verifier its Guidelines); and the line between the two
is who it's for: baloo holds what is useful to everyone, `bagheera` only what is useful to
developers. So baloo is no longer "knowledge only", and there is no thin layer of its own for
other roles: what guards or helps any role is baloo's.

Agreed 2026-10-04: a domain's own plugin is neither this repo's nor this marketplace's: it holds
the domain's private knowledge and has another owner, so it lives with them.

Agreed 2026-10-05: every role works with the knowledge through git alone, in a clone of the code
repo and its `.about/`, with no MCP or other store; baloo targets neither Cowork, where its Hooks
are unreliable, nor cloud sessions of Claude Code.

Settled by deciding:
- whether acceptance gets a plugin or a skill in `akela`;
- which plugin each part goes to under "useful to everyone". Proposed, not agreed: baloo takes
  the knowledge skills, the Session review and the Inbox's count, `retro` with `condense`,
  `doctor` (in both), the Output style, the Status line, `no-secrets-in-context`,
  `no-destructive-commands` and `writing-for-agents` built into its skills; `bagheera` takes
  the code's Guidelines, `architecture`, the Stop check, Format on edit and every Git hook,
  `no-stale-adr-date` too, since two plugins writing `.git/hooks` would overwrite each other;
- one binary for baloo and `bagheera`, or one each from a shared Go module. Proposed: one Go
  module in `src/` with `cmd/baloo` and `cmd/bagheera`, the release tool deciding a plugin's
  Release by `go list -deps` of its `cmd`;
- one repo for every plugin, or a repo per plugin with this one left as the marketplace. Proposed:
  the public plugins stay here, since `bagheera` leans on baloo's skill names and only a test in
  the same repo catches a rename, with a semver, `CHANGELOG.md` and `<name>-v*` tags per plugin
  and `mise run release <name>`;
- a version per plugin, as above, or one version for the whole repo, Lerna's fixed mode, with a
  Release taking only the plugins that changed, so an unchanged plugin's `plugin.json` keeps its
  version and nobody updates for nothing. One version keeps the `v*` tags, the Loader and the
  release tool as they are, makes which `bagheera` works with which baloo obvious, and fits one
  shared binary; its cost is gaps in a plugin's numbers (0.22 to 0.25). Every plugin in every
  Release was argued against: updates for nothing, a major raised by another plugin's breaking
  change, and CHANGELOGs with others' changes;
- how installed copies of baloo learn their Checks and Guidelines moved, with the Config split
  between the plugins.

Then rewrite ADR plugin.

## Session start knows every part of the plugin

2026-10-04 · plugin review · kept 2026-10-04

`sessionStart` in `src/baloo/cmd/baloo/main.go`, about 100 lines, calls each part in turn
(Config, Output style, attribution, Status line, Git hooks, Session review, Inbox, Guidelines)
and writes each one's lines for Claude itself; the Inbox's parsing, `inboxItems`, lives there
too, with no package of its own. So a new part edits `main.go` and `main_test.go` (857 lines).
Settled by deciding whether each package returns its own report lines and `main` only gathers
them, with the Inbox's parsing moved to a package of its own, or the orchestration stays as is.
Kept to decide when the next part joins session start.
