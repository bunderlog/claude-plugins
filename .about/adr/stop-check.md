# The Stop check runs the project's own command after a turn that changed the working tree

Date: 2026-10-01

"Done is verifiable" holds only while Claude remembers to run the project's checks, and a Git
hook catches a failure only at the commit. Where the Config names a command, `stop-check: mise run
check`, the Stop check runs it with `sh -c` in the repo's root when Claude ends a turn that changed
the working tree, and hands a failure back to Claude, with the end of the command's output, to fix
before it stops. Without the key it is off: no command fits every project.

Whether the turn changed the tree is told by a snapshot: at each prompt the binary records, in the
plugin's data folder, HEAD, `git status` and the content of each file it lists, ignored files
excepted, and at the Stop compares. An answer to a question runs nothing, a user's uncommitted
work doesn't send Claude off to fix it, and an edit made through Bash counts as much as one made
with Edit. It blocks at most once a turn: Claude Code marks the Stop after a block, and that one
passes, so a check that can't pass never traps Claude. A Session review's session runs none.

The Stop check is not a Check: it runs the project's command, not the binary's code, so its key is
at the top of the Config, not under `claude-hooks`, and a new Config has it only as a comment.

## Considered options

- No Stop check, the project's own Stop Hook in `.claude/settings.json` — no code here, but it
  runs after every answer, questions too, and each project writes its own.
- A reminder, handed to Claude instead of or beside a failure — nothing tells whether Claude acted
  on it, and it is one more ceremony after each edit.
- Guessing the command, a `mise.toml` with a `check` task or a `package.json` with a `test` script
  — a wrong guess blocks for nothing.
- A list of commands — one line joins them with `&&`, or a task of the project's own.
- Counting only the files Claude's Edit, Write and MultiEdit calls touched — another session's
  edits, such as a Session review's, would not count, but neither would Claude's own made with
  Bash.
- Under `claude-hooks` — that group's keys are `true` or `false` and on without one.

## Consequences

- Another process that changes the tree during Claude's turn, such as a Session review of the
  last session, can make the Stop check run, and block once, for changes Claude didn't make.
- The command runs after every turn that changes a file, so a slow one delays each such turn;
  Claude Code stops it at the Hook's 600 seconds, and the turn ends unchecked.
- Each prompt in a repo with the key runs `git status` and reads the changed files.
- Revisit when such false blocks become common, or when the checks are too slow to run each
  turn.
