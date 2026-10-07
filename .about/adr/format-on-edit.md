# Format on edit runs the project's formatter on each file Claude edits, and says nothing

Date: 2026-10-07

Claude's edits drift from a project's formatting, and a Git hook or CI fails on that only at the
commit or the push. Where the Config names a command, `format-on-edit: npx prettier --write`, a
`PostToolUse` Hook on Edit, Write and MultiEdit runs it with `sh -c` in the repo's root, with the
edited file's path, relative to the root, at the end. It runs only for a file inside the repo, and
not in a Session review's session. Without the key it is off: no command fits every project.

It says nothing of how the command went, to Claude or the user: a lint error halfway through a
change that spans files is no reason to stop Claude, and the project's own checks report what still
fails. It is not a Check: its key is at the top of the Config, and a new Config has it only as a
comment.

## Considered options

- Handing a failure back to Claude after each edit — it catches an error sooner, but interrupts
  every intermediate step of an edit across files.
- No Hook, the project's checks alone — formatting would wait for the commit, and a formatter's
  failure there stops it for a fix the formatter could have made itself.
- The file's path in the command where `{file}` stands — one more rule to learn, for commands that
  all take the path last anyway.

## Consequences

- The formatter changes the file after Claude's edit, so Claude Code may tell Claude the file
  changed, and an Edit that follows may need the file read again.
- The command runs on every edit: a slow one, such as a type-aware ESLint, delays each; it is
  stopped after 50 seconds.
- Revisit when a project needs the formatter's failures handed back, or a command that takes the
  path elsewhere.
