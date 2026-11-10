# The Status line is the plugin's, set by each person in their own settings

Date: 2026-11-10

The plugin ships a Status line: the project's folder and the branch on the left, the context, 5-hour
and 7-day Usage bars and the Cache bar centered, the Cache bar last since nothing in parentheses
closes it, and the model with its effort on the right. The folder is the last part of the path
Claude Code runs in (`workspace.project_dir`, else `current_dir`), not of the folder a command moved
to, so a terminal shows which project, or which worktree of one, a session works in. The plugin
draws it, `run.py status-line`, from what Claude Code gives a status line command on stdin; a line
too narrow shrinks the bars, then drops the reset times, the 5-hour's clock time and the 7-day's
weekday, then the model. Each Usage bar turns yellow and red at percentages, by default the context
at 15 and 20, the 5-hour at 70 and 85, the 7-day at 80 and 95.

The Cache bar reads Claude Code's `prompt_cache`: it fills with the share of the cache's lifetime
left, 5 minutes or an hour, turning yellow below 40% and red below 20% by default, and empty when
cold; beside it are the minutes until the cache goes cold, rounded up, or `cold` in red. Without
the context bar the cache's size follows them, the tokens the next message writes again once it
is cold; it is the context's tokens again, so beside them it would say the same twice. With
caching off it doesn't show. Claude Code runs the line again when the cache goes cold, and the
`statusLine` setting asks it to every 60 seconds besides, so the minutes count down while idle.

It draws its default bars at their default thresholds; no file sets them (PRD no-config). A plugin
can't set Claude Code's `statusLine` itself, and the plugin writes none: each person sets it in
their own `~/.claude/settings.json`, as `python3 -E -s '<plugin data>/baloo/scripts/run.py'
status-line # managed by baloo`. The path is a link in `${CLAUDE_PLUGIN_DATA}` that each session
start points at the running version's plugin folder (ADR binary), so the command stays the same
from one version to the next. Where no settings file Claude Code reads sets `statusLine`, the
first session start in a clone tells Claude, to tell the person, that line, once per clone; a
headless session is told nothing.

## Considered options

- The Config's `status-line` key, with its `bars` and `thresholds`, which session start wrote
  into the clone's `.claude/settings.local.json` where the plugin was enabled (until 2026-11-10) —
  it replaced a person's own line in that repo, and was a switch of the plugin's own beside Claude
  Code's (PRD no-config).
- Giving way, as the Output style does, to a `statusLine` in any settings file — a user with a
  status line of their own for every project would never get the plugin's.
- One list of bars, each a name or a name with its thresholds — shorter, but its
  entries mix two types, which a schema and an editor handle worse.
- Writing the bars into the command's arguments at session start — an edit shows only in the
  next session.
- Writing the file that enables the plugin, as the Output style does — a team's committed
  `.claude/settings.json` would get a path from one person's machine.
- `run.py`'s path in the installed plugin, rewritten at each session start — the path changes
  with every version, so each update rewrites the settings file, and the line breaks in the
  sessions between the update and the rewrite.

- A countdown in seconds, run every second — a Python start and a `git` call each second for a
  number nobody reads to the second.
- The cache's hit ratio, as the prompt-cache-control mod shows it, as the bar or beside it — over
  a session it stays near 98% and says nothing; the time left is what tells whether to send the
  next message now or `/compact` first.
- The last miss's cause beside it for a while after a miss — it seldom tells what to do.

## Consequences

- A person who never sets the line sees none; they are told once per clone.
- A `statusLine` an earlier Release wrote into a clone's `.claude/settings.local.json` overrides
  the person's own until they remove it; `doctor` names it.
- The line runs the plugin without its Hook's `sh`: before the first session start, after the
  plugin's data folder is removed, or where `python3` is missing or older than 3.9, Claude Code
  shows no line.
- Revisit when Claude Code lets a plugin set a status line of its own, or bagheera's visibility
  PRD decides it writes the line with the person's yes.
