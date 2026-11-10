# Each Check a Hook runs is always on

Date: 2026-11-10

The Checks a Hook runs, `no-git-hook-bypass` and `no-secrets-in-context`, are bagheera's (ADR
plugin), and always on, outside a repo too: they guard against accidents where nobody set anything
up, and turning bagheera off is the only way to turn them off (PRD no-config). A `claude-hooks` key
left in an earlier baloo's Config does nothing, and `doctor` names the Config for the user to
delete.

The plugin has no commit Check: those are `hathi`'s, run by a project's own Git hooks and CI (ADR
git-hooks).

A Check only denies; none asks the user first, and nothing asks before a change to Claude Code's
settings that may turn the Checks off (ADR measurement).

One `PreToolUse` Hook, on Bash, Read, Grep, Edit, Write and MultiEdit, runs the plugin's
`pre-tool-use`, which runs both Checks. Each reads the command's words, not a full shell: it
looks past wrappers such as `sudo`, `timeout` and `env`, into `sh -c`, `eval` and command
substitutions, and a pattern such as `.e*` stands for the files it matches; what it can't follow,
such as a file copied first and shown after, goes through. Where `python3` is
missing or the plugin fails, it says nothing, and the call runs: session start has already said
that no Check runs that session (ADR binary).

## Considered options

- Each Check turned on or off by its own key under `claude-hooks`, on without it (until
  2026-11-09) — a committed Config could turn one off for everyone who opened the repo, a Leak
  waiting to happen, for a switch nobody used but in tests.

- The commit Checks under `git-hooks`, run by the Git hooks the plugin wrote, with `baloo check`
  for CI, and session start turning off Claude Code's commit attribution and telling Claude the
  commit format where they were on (until 2026-11-09) — `hathi` has every one of them, and a
  project's committed settings and `CLAUDE.md` say the rest (ADR git-hooks).
- One Check for both jobs, with one key — a bypass of the Git hooks and a Leak into Claude's
  context are unrelated, and one can't be turned off alone.
- Every Check off without its key, the Checks a Hook runs too (until 2026-10-01) —
  one rule for all, but no protection outside a repo or in a Config made before the keys.
- `no-secrets-in-context` always on, with no key — no repo could turn it off, but a false alarm
  would have no way around it.
- Every key under `checks` (until 2026-10-01) — one list for two kinds of Check with opposite
  defaults, which only a comment told apart.
- Each key at the top of the Config — ten keys mixed with the other settings.
- A Hook per Check — a Python start per Check on every Bash call, each reading the Config.
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
- `protected-paths`, asking before Claude edits generated files, lock files or vendored code —
  Claude Code's own `permissions.ask` rules already do.
- `no-edits-outside-repo`, asking before a Write or an Edit outside the repo — Claude Code already
  asks before writing outside its working directories.

## Consequences

- A Config made before 2026-11-09 with `claude-hooks` or `checks` turns nothing off; `doctor` names
  the first as a removed setting, and the second as not a setting.
- Claude can turn a Check off only by turning bagheera off in Claude Code's settings, without a
  question.
- Nothing in the plugin stops a command that destroys work: Claude Code's permissions and its
  auto mode do.
- Revisit when a false alarm would make people turn bagheera off wholesale, or a session shows work
  destroyed that a Check would have stopped.
