# Each Check has a key under the Hook or the Git hooks that run it, and a Hook's are on without one

Date: 2026-10-01

Each Check turns on or off with a key of its own in the Config, named as the Check without the
plugin's prefix and grouped by what runs it: under `claude-hooks`, the Checks a Hook runs,
`no-git-hook-bypass`, `no-destructive-commands` and `no-secrets-in-context`; under `git-hooks`,
the Checks Git hooks run, `no-ai-coauthor`, `conventional-commits`, `no-secrets-in-commits`,
`no-stale-adr-date` and `linear-history`. A key is `true` or `false`; `conventional-commits` also
takes a map of its settings, `types` (a list, or `any`) and `max-length` (0 for none), which turns
it on. The two groups have opposite defaults, and the Stop check runs in a Hook too, not on a
tool call, so they are named for what runs them.

A Check a Git hook runs is off without its key, as ADR config has it: it acts on every commit in
the repo, Claude's or not, so it waits to be asked, and a new Config asks for all of them. The
Checks a Hook runs are on without their key, outside a repo too, where no Config is read, and
`false` turns one off: they guard against accidents where nobody set anything up. A Config that
turns one off is named at every session start, so someone who opens a repo whose committed Config
does so knows.

The plugin writes a Git hook where the Config turns at least one of its Checks on, and takes its
own out where none is; with husky 9 it goes through husky, which it finds by itself (ADR
git-hooks). Writing them has no key of its own. It never changes git's config: `linear-history`,
failing, names `git config pull.rebase true` for the user to run.

Since a Config can turn the Checks a Hook runs off, Claude asks the user before it changes the
Config: a Hook asks first about an Edit, Write or MultiEdit of the Config, and about a Bash command
that names it, unless a program that only reads files, such as `cat`, `grep`, `sed` without `-i`
or `git diff`, reads it with no redirect into it. Claude Code's own settings can turn them off too, with `disableAllHooks` or by
disabling the plugin, so the Hook also asks before a tool call that may do that: an Edit, Write or
MultiEdit of a `settings.json` or `settings.local.json` in a `.claude` folder or in
`$CLAUDE_CONFIG_DIR` whose new text names `disableAllHooks`, `enabledPlugins` or `baloo@`, a Bash
command that names such a file and such a key, or `claude plugin disable` or `uninstall` of the
plugin. These rules have no key.

Where `no-ai-coauthor` is on, session start also sets Claude Code's `attribution` to
`{"commit": ""}`, so Claude writes no co-author trailer the Check would then reject. It writes it
as it picks an Output style (ADR output-styles): where the plugin is enabled, in the settings file
that enables it, and only where none of Claude Code's settings files sets `attribution` or
`includeCoAuthoredBy`, to any value. It never takes it out.

`no-destructive-commands` asks before `git push --delete` (or `git push <remote> :<branch>`), but
lets it pass where the remote's default branch, `<remote>/HEAD` as the repo last fetched it, holds
each branch it deletes whole: deleting a branch after it is merged is a step the user asks for by
name, and a question on each is one to say yes to unread. It looks at the last fetch and doesn't
fetch, so it asks where the branch is ahead, missing from the remote-tracking refs, or the remote's
HEAD is unknown.

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

- One Check for the three jobs, with one key — commands that destroy work, a bypass of
  the Git hooks and a Leak into Claude's context are unrelated, and one can't be turned off alone.
- Every Check off without its key, the Checks a Hook runs too (until 2026-10-01) —
  one rule for all, but no protection outside a repo or in a Config made before the keys.
- `no-secrets-in-context` always on, with no key — no repo could turn it off, but a false alarm
  would have no way around it.
- Every key under `checks` (until 2026-10-01) — one list for two kinds of Check with opposite
  defaults, which only a comment told apart.
- `tool-calls` and `git-hooks` under `checks` — a level that tells nothing apart, and a Stop
  check runs in a Hook but not on a tool call.
- Each key at the top of the Config — eight keys mixed with the other settings.
- A key to turn writing the Git hooks off, or to pick husky over plain Git hooks — where husky 9
  holds `core.hooksPath`, git runs only husky's, and without husky there is nothing to pick; a
  Check on with no Git hook would run only in CI, which calls `baloo check` whatever the key
  says.
- Setting `pull.rebase=true` in the repo's git config where `linear-history` is on and it has
  none — a change to how `git pull` works that nobody asked for, overriding the user's own global
  setting, and git since 2.33 won't merge on a pull anyway until `pull.rebase` or `pull.ff` is
  set.
- A Hook per Check — three runs of the binary on every Bash call, each reading the Config.
- Leaving `no-ai-coauthor` alone to catch the trailer — Claude Code adds it by default, so each
  commit fails once and is written again.
- `attribution.pr` too — the Check reads commits, not pull requests.
- Taking the attribution out where `no-ai-coauthor` goes off — the binary can't tell its value
  from one the user wrote.
- A project's own rules for commands to deny or ask about — no project has asked for them.
- Asking before every change to Claude Code's settings — also covers a key missed here, but
  permissions and env are edited often, and a question on each teaches the user to say yes
  unread.
- Asking about every Bash command that names the Config — it asked on every `cat` and `grep` of
  it, and a question on each read teaches the user to say yes unread.
- Leaving it to Claude Code, which treats `.claude/` as a protected folder — its docs don't say
  it asks in every permission mode, and a Bash edit goes around a rule on Edit and Write.

## Consequences

- A Config made before the keys, or with them under `checks`, gets the Checks a Hook runs, and
  the Git hooks' only once its user adds their keys; `checks` is reported as not a setting.
- A repo's committed Config can turn a Check off for everyone who opens it; session start says
  so, but doesn't stop it.
- Claude asks the user before every change to the Config, a harmless one too.
- A Bash command that writes the Config through a program not known to write, such as
  `git diff --output`, goes unasked.
- Turning `no-ai-coauthor` off leaves the attribution off, until someone takes it out.
- A commit pushed to a merged branch since the last fetch is deleted with it, unasked.
- A tool call that turns the Hooks off in a way the rules don't name, such as a script that
  writes the key, goes unasked; they guard against accidents, not against Claude.
- Managed settings and the `/plugin` menu are out of reach: one needs an administrator, the other
  is the user's own.
- Revisit when a false alarm makes people turn a Check a Hook runs off wholesale, or a
  committed Config that turns one off leads to a Leak, and when Claude Code asks before every
  change to its own settings.
