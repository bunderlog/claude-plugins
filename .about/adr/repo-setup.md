# This repo is set up as any project is: its Git hooks in `.githooks/` run `hathi`

Date: 2026-11-09

This repo is set up by PRD project-setup like any project that uses the plugins: its Git hooks
are the scripts in `.githooks/`, each running `hathi check <hook>` as `hathi hooks print` prints
it, `hathi` pinned exactly in `mise.toml`, with `.hathi.yml` listing the commit types in full for
`CLAUDE.md` to import, and CI runs `hathi` over each push and pull request. Each clone turns the
hooks on once with `git config core.hooksPath .githooks`, as the README says.

It moved off what baloo wrote on 2026-11-09: the Git hooks baloo wrote into `.git/hooks`, which
ran `hathi` through `git-hook-commands` and baloo's own `no-stale-adr-date`; the committed
`outputStyle`; and the Status line baloo set in `.claude/settings.local.json`. `.claude/baloo.yml`
stays, with the Output style, the Status line and every Git hook Check off and no Git hook
command, until baloo works without a Config (Issue config-out-of-baloo).

## Considered options

- Running `hathi` through baloo's Git hooks, as until 2026-11-09 — the hooks lived untracked in
  each clone and ran only where baloo had a session first, and a commit's checks came from two
  tools.
