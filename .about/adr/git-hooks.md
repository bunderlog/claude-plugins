# The plugin writes the Git hooks at session start, each running the binary through a fixed link

Date: 2026-10-01

At session start the binary writes `pre-commit`, `commit-msg` and `pre-push` into the folder
`git rev-parse --git-path hooks` names, each where the Config turns at least one of its Checks on
(ADR checks), and takes out its own where none is. A Git hook it wrote is a short `sh` script
marked `# managed by baloo` that runs `baloo git-hook <hook>` by the absolute path of a link in the
plugin's data folder, which session start points at the running binary: the path stays the same
from one version to the next, and git clients that run hooks with a minimal PATH find it. The
binary reads the Config at each run and runs the hook's Checks it turns on, all of them, failing
when one fails; where the link is gone, the Git hook says so and passes.

A Git hook already there that the plugin didn't write is left alone, and every session start
names the Checks it keeps from running. Where the folder is inside the working tree, the plugin
adds each Git hook it writes to `.git/info/exclude`.

With husky 9, whose `core.hooksPath` is `.husky/_` holding its `h`, git runs only husky's Git
hooks, so the plugin writes its own into the git folder's `baloo-hooks/` and puts one marked line
first in husky's `.husky/<hook>`, created when missing, which runs the plugin's Git hook if it is
there. The line is the same in every clone, so it is committed, and session start says so; the
plugin takes the line out where the Git hook goes.

A Session review's session writes no Git hook: the repo's are the user's session's to write.

## Considered options

- The Checks' own commands in the Git hook, `baloo check <name>` for each — a Git hook for each
  set of Checks, rewritten at each change to the Config.
- A path into one version's binary — the Git hooks break with each update until the next session
  start.
- The binary found on PATH — git GUI clients run hooks with a minimal one.
- Overwriting a Git hook of someone else's, or chaining to it — another tool's, or a person's,
  file changed behind their back.
- With husky: writing into `.husky/_`, which husky rewrites at every install; the Checks'
  commands in `.husky/<hook>`, a committed absolute path into one person's data folder; only
  telling the user which line to add, a manual step for a line that never changes.
- `core.hooksPath` pointed at a folder of the plugin's — it would take over from husky, lefthook
  or the repo's own setting.

## Consequences

- A Check turned off stops at once, but one turned on whose Git hook isn't written waits for the
  next session start.
- A teammate who clones the repo without the plugin gets no Git hooks; with husky, the committed
  line does nothing for them.
- With husky, pre-push's input goes to the plugin's Git hook, the first line, so a pre-push
  command of the project's own after it reads none. Husky 8, lefthook and pre-commit are Git hooks
  of someone else's.
- Local Git hooks can be bypassed (`--no-verify`, a clone without the plugin):
  `no-git-hook-bypass` stops Claude from doing so, and CI running `baloo check` is the real
  enforcement (ADR checks).
- Revisit when someone with lefthook, pre-commit or husky 8 wants the Checks in their Git hooks.
