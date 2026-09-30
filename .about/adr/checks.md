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
is read, and `false` turns one off: they guard against accidents where nobody set anything up,
as the old plugin's Guard did everywhere. A Config that turns one off is named at every session
start, so someone who opens a repo whose committed Config does so knows.

Since a Config can turn those Checks off, Claude asks the user before it changes the Config: a
Hook asks first about an Edit, Write or MultiEdit of the Config, and about a Bash command that
names it. This rule has no key.

One `PreToolUse` Hook, on Bash, Read, Grep, Edit, Write and MultiEdit, runs the binary's
`pre-tool-use`, which reads the Config once and runs the Checks it turns on; a denial wins over a
question to the user. Where the binary is missing or fails, it says nothing, and the call runs:
session start has already said that no Check runs that session (ADR binary).

## Considered options

- Guard, one Check for the three jobs, with one key — commands that destroy work, a bypass of
  the Git hooks and a Leak into Claude's context are unrelated, and one can't be turned off alone.
- Every Check off without its key, the Checks on Claude's tool calls too (until 2026-10-01) —
  one rule for all, but no protection outside a repo or in a Config made before the keys.
- `no-secrets-in-context` always on, with no key — no repo could turn it off, but a false alarm
  would have no way around it.
- The keys at the top of the Config — shorter, but eight keys mixed with the other settings.
- A Hook per Check — three runs of the binary on every Bash call, each reading the Config.
- A project's own rules for commands to deny or ask about, as the old plugin's Guard had — no
  project used them.

## Consequences

- A Config made before the keys gets the Checks on Claude's tool calls, and the Git hooks' only
  once its user adds their keys.
- A repo's committed Config can turn a Check off for everyone who opens it; session start says
  so, but doesn't stop it.
- Claude asks the user before every change to the Config, a harmless one too.
- Claude Code's `disableAllHooks` still turns every one of them off (glossary, Unresolved).
- Revisit when a false alarm makes people turn a Check on Claude's tool calls off wholesale, or a
  committed Config that turns one off leads to a Leak.
