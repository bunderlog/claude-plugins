# Each Check has a key under `checks`, and the Checks on Claude's tool calls are on without one

Date: 2026-10-01

Each Check turns on or off with a key of its own under `checks` in the Config, named as the Check
without the plugin's prefix: `no-ai-coauthor`, `conventional-commits`, `no-secrets-in-commits`,
`no-stale-adr-date` and `linear-history`, which Git hooks run, and `no-git-hook-bypass`,
`no-destructive-commands` and `no-secrets-in-context`, which a Hook runs on Claude's tool calls. A
key is `true` or `false`; `conventional-commits` also takes a map of its settings, `types` (a
list, or `any`) and `max-length` (0 for none), which turns it on.

A Check a Git hook runs is off without its key, as ADR config has it: it acts on every commit in
the repo, Claude's or not, so it waits to be asked, and a new Config asks for all of them. The
three Checks on Claude's tool calls are on without their key, outside a repo too, where no Config
is read, and `false` turns one off: they guard against accidents where nobody set anything up. A
Config that turns one off is named at every session start, so someone who opens a repo whose
committed Config does so knows.

Since a Config can turn those Checks off, Claude asks the user before it changes the Config: a
Hook asks first about an Edit, Write or MultiEdit of the Config, and about a Bash command that
names it. Claude Code's own settings can turn them off too, with `disableAllHooks` or by
disabling the plugin, so the Hook also asks before a tool call that may do that: an Edit, Write or
MultiEdit of a `settings.json` or `settings.local.json` in a `.claude` folder or in
`$CLAUDE_CONFIG_DIR` whose new text names `disableAllHooks`, `enabledPlugins` or `baloo@`, a Bash
command that names such a file and such a key, or `claude plugin disable` or `uninstall` of the
plugin. These rules have no key.

One `PreToolUse` Hook, on Bash, Read, Grep, Edit, Write and MultiEdit, runs the binary's
`pre-tool-use`, which reads the Config once and runs the Checks it turns on; a denial wins over a
question to the user. Where the binary is missing or fails, it says nothing, and the call runs:
session start has already said that no Check runs that session (ADR binary).

`baloo check <name>` takes the input its Git hook gets, so a project's CI can run the same Checks
on commits made where the Git hooks didn't run, as the README's CI section shows; this repo's CI
does, with the binary built from the checked commit. `no-stale-adr-date` is left out there (ADR
adr-format). That input follows the Git hooks and is not a promised interface, so a CI pins a
Release.

## Considered options

- Guard, one Check for the three jobs, with one key — commands that destroy work, a bypass of
  the Git hooks and a Leak into Claude's context are unrelated, and one can't be turned off alone.
- Every Check off without its key, the Checks on Claude's tool calls too (until 2026-10-01) —
  one rule for all, but no protection outside a repo or in a Config made before the keys.
- `no-secrets-in-context` always on, with no key — no repo could turn it off, but a false alarm
  would have no way around it.
- The keys at the top of the Config — shorter, but eight keys mixed with the other settings.
- A Hook per Check — three runs of the binary on every Bash call, each reading the Config.
- A project's own rules for commands to deny or ask about — no project has asked for them.
- Asking before every change to Claude Code's settings — also covers a key missed here, but
  permissions and env are edited often, and a question on each teaches the user to say yes
  unread.
- Leaving it to Claude Code, which treats `.claude/` as a protected folder — its docs don't say
  it asks in every permission mode, and a Bash edit goes around a rule on Edit and Write.

## Consequences

- A Config made before the keys gets the Checks on Claude's tool calls, and the Git hooks' only
  once its user adds their keys.
- A repo's committed Config can turn a Check off for everyone who opens it; session start says
  so, but doesn't stop it.
- Claude asks the user before every change to the Config, a harmless one too.
- A tool call that turns the Hooks off in a way the rules don't name, such as a script that
  writes the key, goes unasked; they guard against accidents, not against Claude.
- Managed settings and the `/plugin` menu are out of reach: one needs an administrator, the other
  is the user's own.
- Revisit when a false alarm makes people turn a Check on Claude's tool calls off wholesale, or a
  committed Config that turns one off leads to a Leak, and when Claude Code asks before every
  change to its own settings.
