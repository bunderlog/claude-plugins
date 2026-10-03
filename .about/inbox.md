## Guidelines for more stacks

2026-10-03 · user

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. Settled by deciding
which stacks get one, each with its stack detection for a new Config, or none.

## Guidelines for concerns across stacks

2026-10-03 · user

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as Guidelines. Settled by deciding which earn a Guideline
of their own rather than rules in `principles` or `design`, and whether a new Config turns them on.

## A Check for protected paths

2026-10-03 · user

`protected-paths` under `claude-hooks`: ask before Claude edits generated files, lock files or
vendored code, with the paths in the Config. Settled by deciding whether it's worth a Check, and
how the Config names the paths — a key under `claude-hooks` takes only `true` or `false` today
(ADR checks).

## A Check for edits outside the repo

2026-10-03 · user

`no-edits-outside-repo` under `claude-hooks`: ask before a Write or an Edit outside the repo's
root. Settled by deciding whether Claude Code's own permissions already cover it, and what passes
(the scratchpad, `~/.claude/`).

## A Check for conflict markers

2026-10-03 · user

`no-conflict-markers` under `git-hooks`: refuse a commit whose staged changes hold `<<<<<<<`,
`=======` or `>>>>>>>` lines. Settled by deciding it, and how a file that holds them on purpose,
such as a test fixture, passes.

## A Check for large files

2026-10-03 · user

`no-large-files` under `git-hooks`: refuse a commit that adds a file over a size. Settled by
deciding it and the size's default, and whether it takes a setting, as `conventional-commits` does.

## A Check for a commit's PRD

2026-10-03 · user

`prd-reference` under `git-hooks`: a commit that changes a feature with a PRD in `.about/prd/`
names it in its body, `PRD <feature>`; today only this repo's CLAUDE.md says so. Settled by
deciding how a Check would tell which feature a commit changes, or that it can't and the rule stays
text.

## One command for the Checks of a range of commits

2026-10-03 · user

`baloo check-range $BASE` would run every Check of the Git hooks the Config turns on over the
commits from `$BASE` to `HEAD`, so README's CI script shrinks to the download and one line. A
GitHub Action could wrap both. Settled by deciding the command and its interface, which README now
says isn't promised, and whether an Action is worth its own repo and versions.

## A skill to show a newcomer around

2026-10-03 · user

An `onboard` skill: a tour of the project for someone new, from `.about/` (ADRs, glossary, PRDs)
and the code. Settled by deciding whether it's a skill or a question Claude already answers with
`.about/` at hand.

## A second Output style

2026-10-03 · user

A fuller Output style beside `short-replies`, explaining or teaching, for those who find it too
terse. Settled by deciding whether one is asked for and what it would say.

## The Git hooks run an older binary than the plugin

2026-10-03 · session

In this repo, on 2026-10-03, with the plugin at 0.18.0 (Release published), `.git/hooks/pre-commit`
ran `~/.claude/plugins/data/baloo-bunderlog/baloo`, a link to `baloo_0.15.1_darwin_arm64`, and no
0.16–0.18 binary was in that folder (0.16.0 was in `baloo-inline/`). So the Git hooks ran 0.15.1's
Checks and nothing said so. Settled by finding why session start didn't download 0.18.0 and point
the link at it, or where that session's `CLAUDE_PLUGIN_DATA` was.
