# A project set up for bunderlog's plugins commits everything its Setup needs, the same way in each

## Problem

A project's Setup came from what baloo's session start wrote: a Config, settings and Git hooks in
`.git/hooks`, untracked and frozen at the plugin's version of the clone's first session, so six
projects had five different Git hook setups on 2026-11-09, a teammate's clone got none of it until
their own first session, and nothing said when a project counts as set up (PRD harness).

## Users

- The person who sets a project up: by hand from this PRD until bagheera's setup skill does it.
- Everyone who clones a set-up project: they get its Setup from the commit, and turn its Git hooks
  on once.
- Not for: a repository whose owner decides not to set it up, such as a fork whose upstream owns
  `CLAUDE.md`; it stays not set up, and is told so once per clone.

## Success signal

Each git repository worked on from the maintainer's machine since 2026-10-01, as Claude Code's
Transcripts list them, is set up by the list below, or named with why it isn't in Issue
commit-checks-to-hathi; and `hathi doctor` reports no problem in each that has `hathi`.

## Scope

- A project has `hathi` when it commits `.hathi.yml`.
- A set-up project commits:
  - `.claude/settings.json` with:
    - `extraKnownMarketplaces.bunderlog` from GitHub, `bunderlog/claude-plugins`, and
      `enabledPlugins` with `baloo@bunderlog`; once louie ships, `louie@bunderlog` and
      `enableWorkflows` too;
    - `permissions.deny` on reading Env files and private keys, the list below;
    - `attribution` with an empty `commit` and `pr`;
    - no `statusLine` and no `outputStyle`.
  - `CLAUDE.md`, made if missing, with a line that imports the file setting the commit format:
    `@.hathi.yml` where the project has `hathi`, else the project's own (a commitlint config);
    with neither, no line.
  - Where it has `hathi`, `.hathi.yml` listing `conventional-commits`' types in full, so Claude
    reads the format from it; every other Check at `hathi`'s defaults, on.
  - Git hooks in a folder the project commits: `.githooks/` by default, or the husky or lefthook
    setup the project already has, which then runs them. With `hathi`, `commit-msg`,
    `pre-commit` and `pre-push` each run `hathi check <hook>` first, as `hathi hooks print <hook>`
    prints it, then whatever the project's hook ran before. Without `hathi`, `pre-commit` checks
    for Secrets with the project's own tool. Any other hook manager stays, with `hathi` added the
    same way; one with no folder the project commits moves to `.githooks/`.
  - The one command that turns the Git hooks on in a clone, in the README's section on
    development, or in `CLAUDE.md` where the project has no README: `git config core.hooksPath
    .githooks` for `.githooks/`; for husky or lefthook, the install step the project already has.
  - `.about/proposals/` in `.gitignore`.
  - Where it has `hathi` and a `mise.toml`, `"github:bunderlog/hathi"` pinned there to an exact
    version, 1.2.0 or later.
  - An ADR in its `.about/adr/` that says whether it runs `hathi`, what checks Secrets where it
    doesn't, and how it moved off what baloo wrote.
- `permissions.deny` holds `Read` rules for `**/.env`, `**/.env.local`, `**/.env.*.local`,
  `**/.env.development`, `**/.env.production`, `**/.env.staging`, `**/.env.test`, `**/.envrc`,
  `**/*.pem`, `**/*.key`, `**/id_rsa`, `**/id_ed25519`, `~/.ssh/id_*` and `~/.aws/credentials`;
  a template (`.env.example`, `.env.sample`) stays readable. A `~/` rule is relative to each
  person's home, not a path into anyone's.
- A clone's Git hooks are on when git runs hooks from the committed folder: `core.hooksPath` is
  `.githooks`, husky's `.husky/_`, or lefthook has installed its hooks. The person runs the one
  command, never a plugin.
- Setting a project up removes what baloo wrote before: its Git hooks in `.git/hooks` (each begins
  with the line `# managed by baloo`) or its line in husky's, a committed `outputStyle`, and a
  `statusLine` or `outputStyle` in the clone's `.claude/settings.local.json`, and
  `.claude/baloo.yml`, which baloo reads no longer (PRD no-config).
- A project that wants its formatter run on Claude's edits commits its own `PostToolUse` Hook on
  Edit, Write and MultiEdit in `.claude/settings.json`, running the formatter on the edited file.
- First by hand, from this list; bagheera's setup skill does the same once it ships, and when the
  list grows, bagheera's `doctor` names a set-up project that lacks a new item.

## Non-goals

- Installing `hathi` or mise on a machine: the person does, with mise or brew.
- Turning a clone's Git hooks on: the person runs the one command.
- The setup skill itself: it ships with bagheera (Issue split-bagheera-louie).
- Choosing a project's other hooks (lint, tests): they stay as the project has them.
- What a hook does when `hathi` isn't installed: it fails, so the person installs it; `hathi`'s own
  repo decides whether that changes.

## Anti-goals

- A set-up project depends on a file outside the repo, or on an absolute path into a home folder.
- Two set-up projects that both have `hathi` run it differently from their hooks, beyond the folder
  layout they already had.

## Acceptance criteria

- In a set-up project, reading the committed files shows each item of the list: the marketplace,
  baloo on, the deny rules, attribution off, no `statusLine` or `outputStyle`; the import in
  `CLAUDE.md`; `.hathi.yml` with its types, where it has `hathi`; the hook folder with `hathi
  check <hook>` first in each hook; the command in the README; `.about/proposals/` in
  `.gitignore`; the exact `hathi` pin; the ADR; and no `.claude/baloo.yml`. Checked by hand.
- In a fresh clone of a set-up project with `hathi`, after the README's command, a commit with the
  message `wip` and a commit that adds a made-up AWS access key ID (`AKIA` and 16 random
  characters from A–Z and 2–7, not a published example) are each refused, and `hathi doctor`
  reports no problem. Checked by hand.
- In a set-up project, with baloo turned off, Claude's `cat .env`, `head .env.local` and `cat
  id_rsa` are refused, and `cat .env.example` is not. Checked by hand.
- A person on a machine with Claude Code but not baloo who clones a set-up project, opens it and
  trusts the folder has baloo on in the next session (PRD harness). Checked by hand on a clean
  machine.
- In a set-up project, after a session start and a commit with baloo 0.35.0 or later, the committed
  hooks folder is as committed, no file in `.git/hooks` begins with `# managed by baloo`, and
  `.claude/settings.local.json` sets no `statusLine` or `outputStyle`. Checked by hand.
