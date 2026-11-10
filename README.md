# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins, released together under one version: `baloo`,
the project's method, and `louie`, its working rules for building, which a project turns on for
everyone in it, and `bagheera`, each person's session machinery, which each person installs once
(ADR plugin). Each is described in its `plugin.json`.

It is for developers who work with Claude Code across several projects and want the same
discipline in each: decisions, terms and requirements recorded in the project's `.about/`, Secrets
kept out of Claude's context, and one set of working rules and one reply style for Claude. Commits
are checked by [`hathi`](https://github.com/bunderlog/hathi), from a project's own Git hooks and
CI.

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install bagheera@bunderlog
claude plugin install baloo@bunderlog --scope project
claude plugin install louie@bunderlog --scope project
```

bagheera's and louie's Hooks run their Python code, so they need `python3` 3.9 or later, which a Mac
gets with the Command Line Tools and most Linux distributions have; nothing else is installed.

Why things are the way they are is in [.about/adr/](.about/adr/).

## Git hooks

No plugin writes a Git hook: a project's own, committed in `.githooks/`, run `hathi`, and its CI
runs the same `hathi` (PRD project-setup). A Git hook an earlier baloo wrote into `.git/hooks`
now lets each commit through, saying so and how to remove it.

## Settings

The plugins have none of their own: each is on, whole, where Claude Code's `enabledPlugins` turns it
on (PRD no-config). Your Output style and Status line are yours, in `~/.claude/settings.json`;
session start tells you once per clone the lines to add. An old `.claude/baloo.yml` is no longer
read, and `/bagheera:doctor` names it for you to remove. To run a formatter on Claude's edits, a
project adds its own `PostToolUse` Hook to its `.claude/settings.json`.

louie's Workflows, such as `/louie:verify`, run only where Claude Code's dynamic workflows are on:
`"enableWorkflows": true` in the project's `.claude/settings.json`, which setting a project up
adds. Where they are off, Claude runs the `louie:verifier` agent by name instead.

## Doctor

`/bagheera:doctor`, or asking Claude what bagheera has on or why a Check didn't run, shows its
state in the repo: its problems first, each with what fixes it, then its version and the link the
Status line runs, the Session review's Proposals and the Checks. It changes nothing.

## Development

This repo uses its own plugins: `.claude/settings.json` installs `baloo` and `louie` from GitHub,
so a session here runs their last Release. To try an edit before a Release, start a session with
`claude --plugin-dir plugins/baloo --plugin-dir plugins/louie --plugin-dir plugins/bagheera`: their
Hooks, and bagheera's Status line from then on, run this checkout's code. The code is in each
plugin's `scripts/`, the tests in `tests/<plugin>/`, and `mise run check` runs them on Python 3.9
and lints the Python and the Hooks' `sh`. To make a Release of all three and push it, run `mise run
release`.

The repo's own Git hooks are in `.githooks/` and run `hathi`, which `mise.toml` pins; turn them on
once per clone with `git config core.hooksPath .githooks`.
