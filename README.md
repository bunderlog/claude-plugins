# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins. It holds one plugin, `baloo`, described in
its [plugin.json](plugins/baloo/.claude-plugin/plugin.json).

It is for developers who work with Claude Code across several projects and want the same
discipline in each: decisions, terms and requirements recorded in the project's `.about/`, Secrets
kept out of Claude's context, and one set of working rules and one reply style for Claude. Commits
are checked by [`hathi`](https://github.com/bunderlog/hathi), from a project's own Git hooks and
CI.

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install baloo@bunderlog
```

Its Hooks run its Python code, so they need `python3` 3.9 or later, which a Mac gets
with the Command Line Tools and most Linux distributions have; nothing else is installed.

Why things are the way they are is in [.about/adr/](.about/adr/).

## Git hooks

The plugin writes no Git hook: a project's own, committed in `.githooks/`, run `hathi`, and its CI
runs the same `hathi` (PRD project-setup). A Git hook an earlier Release wrote into `.git/hooks`
now lets each commit through, saying so and how to remove it.

## Settings

baloo has none of its own: all of it is on where Claude Code's `enabledPlugins` turns it on (PRD
no-config). Your Output style and Status line are yours, in `~/.claude/settings.json`; session
start tells you once per clone the lines to add. An old `.claude/baloo.yml` is no longer read, and
`/baloo:doctor` names it for you to remove. To run a formatter on Claude's edits, a project adds its
own `PostToolUse` Hook to its `.claude/settings.json`.

## Doctor

`/baloo:doctor`, or asking Claude what baloo has on or why a Check didn't run, shows the plugin's
state in the repo: its problems first, each with what fixes it, then the plugin's version and the
link the Status line runs, the Session review, the Checks and the Guidelines that fit the repo. It
changes nothing.

## Development

This repo uses its own plugin: `.claude/settings.json` installs `baloo` from GitHub, so a session
here runs its last Release. To try an edit to a skill, the agent, a Guideline or a Hook before a
Release, start a session with `claude --plugin-dir plugins/baloo`: its Hooks, and the Git hooks
and Status line from then on, run this checkout's code. The code is in `plugins/baloo/scripts/`,
its tests in `tests/`, and `mise run check` runs them on Python 3.9 and lints the Python and the
Hooks' `sh`. To make a Release and push it, run `mise run release`.

The repo's own Git hooks are in `.githooks/` and run `hathi`, which `mise.toml` pins; turn them on
once per clone with `git config core.hooksPath .githooks`.
