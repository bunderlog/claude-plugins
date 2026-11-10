# baloo runs no formatter on Claude's edits: a project's own Hook does

Date: 2026-11-10

Claude's edits drift from a project's formatting, and a Git hook or CI fails on that only at the
commit or the push. A project that wants its formatter run on each file Claude edits adds its own
`PostToolUse` Hook on Edit, Write and MultiEdit to its committed `.claude/settings.json`, running
its formatter on the edited file: Claude Code's own mechanism, the same for everyone in the project
(PRD no-config, PRD project-setup). baloo runs none.

## Considered options

- Format on edit, the plugin's `PostToolUse` Hook running the command `format-on-edit` named in
  the Config with `sh -c` on each file Claude edited, saying nothing of how it went (until
  2026-11-10) — a Config key that did what a project's own Hook does, and went with the Config.
