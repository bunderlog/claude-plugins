# Each Check has a key under the Hook or the Git hooks that run it, and a Hook's are on without one

Date: 2026-10-09

Each Check turns on or off with a key of its own in the Config, named as the Check without the
plugin's prefix and grouped by what runs it: under `claude-hooks`, the Checks a Hook runs,
`no-git-hook-bypass` and `no-secrets-in-context`; under `git-hooks`, the Checks Git hooks run,
`no-ai-coauthor`, `conventional-commits`, `no-secrets-in-commits`, `no-stale-adr-date`,
`no-conflict-markers`, `no-large-files` and `linear-history`. A key is `true` or `false`;
`conventional-commits` also takes a map of its settings, `types` (a list, or `any`) and `max-length`
(0 for none), and `no-large-files` one of `max-size` (in KB, 1024 without it), which turns it on.
The two groups have opposite defaults, so they are named for what runs them.

A Check a Git hook runs is off without its key, as ADR config has it: it acts on every commit in
the repo, Claude's or not, so it waits to be asked, and a new Config asks for all of them. The
Checks a Hook runs are on without their key, outside a repo too, where no Config is read, and
`false` turns one off: they guard against accidents where nobody set anything up. A Config that
turns one off is named at every session start, so someone who opens a repo whose committed Config
does so knows.

The plugin writes a Git hook where the Config turns at least one of its Checks on, or sets its
command under `git-hook-commands`, which is not a Check (ADR git-hooks), and takes its own out
where neither is; with husky 9 it goes through husky, which it finds by itself (ADR
git-hooks). Writing them has no key of its own. It never changes git's config: `linear-history`,
failing, names `git config pull.rebase true` for the user to run.

A Check only denies; none asks the user first, and nothing asks before a change to the Config or
to Claude Code's settings that may turn the Checks off (ADR measurement).

Where `no-ai-coauthor` is on, session start also sets Claude Code's `attribution` to
`{"commit": ""}`, so Claude writes no co-author trailer the Check would then reject. It writes it
as it picks an Output style (ADR output-styles): where the plugin is enabled, in the settings file
that enables it, and only where none of Claude Code's settings files sets `attribution` or
`includeCoAuthoredBy`, to any value. It never takes it out.

`no-conflict-markers` takes the markers from git's own `diff --check`, so a file whose
`conflict-marker-size` in `.gitattributes` is longer, such as a test fixture, passes; it names a
file's markers only where one of them is `<<<<<<<` or `>>>>>>>`, since git counts a Markdown
heading underlined with seven `=` too. `no-large-files` looks only at files a commit adds: one
already committed passes when it changes or is renamed, since it was let in once.

One `PreToolUse` Hook, on Bash, Read, Grep, Edit, Write and MultiEdit, runs the binary's
`pre-tool-use`, which reads the Config once and runs the Checks it turns on. Where the binary is
missing or fails, it says nothing, and the call runs: session start has already said that no Check
runs that session (ADR binary).

`baloo check <name>` takes the input its Git hook gets, so a project's CI can run the same Checks
on commits made where the Git hooks didn't run, as the README's CI section shows; this repo's CI
does, with the binary built from the checked commit. `no-stale-adr-date` is left out there (ADR
adr-format). That input follows the Git hooks and is not a promised interface, so a CI pins a
Release.

## Considered options

- One Check for both jobs, with one key — a bypass of the Git hooks and a Leak into Claude's
  context are unrelated, and one can't be turned off alone.
- Every Check off without its key, the Checks a Hook runs too (until 2026-10-01) —
  one rule for all, but no protection outside a repo or in a Config made before the keys.
- `no-secrets-in-context` always on, with no key — no repo could turn it off, but a false alarm
  would have no way around it.
- Every key under `checks` (until 2026-10-01) — one list for two kinds of Check with opposite
  defaults, which only a comment told apart.
- `tool-calls` and `git-hooks` under `checks` — a level that tells nothing apart.
- Each key at the top of the Config — ten keys mixed with the other settings.
- A key to turn writing the Git hooks off, or to pick husky over plain Git hooks — where husky 9
  holds `core.hooksPath`, git runs only husky's, and without husky there is nothing to pick; a
  Check on with no Git hook would run only in CI, which calls `baloo check` whatever the key
  says.
- Setting `pull.rebase=true` in the repo's git config where `linear-history` is on and it has
  none — a change to how `git pull` works that nobody asked for, overriding the user's own global
  setting, and git since 2.33 won't merge on a pull anyway until `pull.rebase` or `pull.ff` is
  set.
- A Hook per Check — a run of the binary per Check on every Bash call, each reading the Config.
- Leaving `no-ai-coauthor` alone to catch the trailer — Claude Code adds it by default, so each
  commit fails once and is written again.
- `attribution.pr` too — the Check reads commits, not pull requests.
- Taking the attribution out where `no-ai-coauthor` goes off — the binary can't tell its value
  from one the user wrote.
- A project's own rules for commands to deny or ask about — no project has asked for them.
- `no-destructive-commands` (until 2026-10-07), denying a Bash command that destroys work beyond
  undo, such as `git push --force`, `rm -rf /` or `git reset --hard` with changes to lose, and
  asking before `git push --delete` of an unmerged branch — of its two denials in about three
  weeks (ADR measurement), Claude reached the same effect another way once, and Claude Code's
  auto mode classifier refuses the same commands itself.
- Asking the user before a change to the Config, or to Claude Code's settings that may turn the
  Hooks off (`disableAllHooks`, `enabledPlugins`, `claude plugin disable`), and before
  `no-destructive-commands`' commands to ask about (until 2026-10-07) — the user allowed 11 of
  its 12 questions (ADR measurement): friction, not protection, and a question said yes to
  unread. Asking about every Bash command that names the Config, or every change to Claude
  Code's settings, asked more and taught the same.
- Matching conflict markers in the diff itself — a file that holds them on purpose would need a
  mark of the plugin's own, where git already reads one from `.gitattributes`; `-whitespace`
  there doesn't exempt a file from git's check, `conflict-marker-size` does.
- `no-large-files` on a file that grows past its limit too — a file committed on purpose would
  fail again at each change, until its limit is raised for every file.
- `protected-paths`, asking before Claude edits generated files, lock files or vendored code —
  Claude Code's own `permissions.ask` rules already do.
- `no-edits-outside-repo`, asking before a Write or an Edit outside the repo — Claude Code already
  asks before writing outside its working directories.
- `prd-reference`, refusing a commit that changes a feature with a PRD but doesn't name it — a
  Check can't tell which feature a commit changes, so the rule stays text in CLAUDE.md.

## Consequences

- A Config made before the keys, or with them under `checks`, gets the Checks a Hook runs, and
  the Git hooks' only once its user adds their keys; `checks` is reported as not a setting.
- A repo's committed Config can turn a Check off for everyone who opens it; session start says
  so, but doesn't stop it.
- Claude can change the Config, or Claude Code's settings, and so turn a Check off, without a
  question; session start names a Config that turns a Check a Hook runs off.
- Nothing in the plugin stops a command that destroys work: Claude Code's permissions and its
  auto mode do.
- Turning `no-ai-coauthor` off leaves the attribution off, until someone takes it out.
- Revisit when a false alarm makes people turn a Check a Hook runs off wholesale, a committed
  Config that turns one off leads to a Leak, or a session shows work destroyed that a Check
  would have stopped.
