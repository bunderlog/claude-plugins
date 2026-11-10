# The Status line is the plugin's, set by each person in their own settings

Date: 2026-11-11

The plugin ships a Status line: the project's folder and the branch on the left, with `±5` for the
entries `git status` lists and `↑2` for the commits not pushed (PRD status-line); the context,
5-hour and 7-day Usage figures and the Cache figure centered; and on the right how many sessions
wait for their person and how many of the machine's projects need attention (PRD visibility), and `⇡
0.54` where a newer version is installed than the session started on, for the project or, outside a
repo, for the user, which only a restart runs, then the model with its effort. Each figure is an
icon and a number in place of a label and a bar: `▤ 12% 120K` the context with its tokens, `◷ 42%
02:42` the 5-hour limit with when it resets, `◷ 61% Sat` the 7-day one with the weekday it resets
on, `↻ 40m` the cache; `⧗ 3` the sessions waiting and `⚑ 2` the projects, each only when it isn't 0.
The groups of the middle and of the right are a grey `·` apart, as Claude Code's own footer has it,
a group's parts a space. The whole line is grey while all is well, `±` and `↑` too, as work in
progress is; a figure's icon and number turn yellow and red together at its thresholds, the details
after it stay grey, and `⧗`, `⚑` and `⇡` are yellow, since each shown is something to do. The folder
is the last part of the path Claude Code runs in (`workspace.project_dir`, else `current_dir`), not
of the folder a command moved to, so a terminal shows which project, or which worktree of one, a
session works in. The plugin draws it, `run.py status-line`, from what Claude Code gives a status
line command on stdin; a line too narrow drops the details, then the model, then cuts the folder's
name short, then drops the figures, and keeps `±`, `↑`, `⧗`, `⚑` and `⇡`. Each Usage figure turns
yellow and red at percentages, by default the context at 15 and 20, the 5-hour at 70 and 85, the
7-day at 80 and 95.

The Cache figure reads Claude Code's `prompt_cache`: the minutes until the cache goes cold, rounded
up, or `cold`, turning yellow below 40% of its lifetime left, 5 minutes or an hour, red below 20%
and when cold, by default. Without the context the cache's size follows them, the tokens the next
message writes again once it is cold; it is the context's tokens again, so beside them it would say
the same twice. With caching off it doesn't show. Claude Code runs the line again when the cache
goes cold, and the `statusLine` setting asks it to every 60 seconds besides, so the minutes count
down while idle.

The branch, `±` and `↑` are of the folder Claude Code is in, as the branch always was, and come from
`git` run each time the line draws, side by side, `status --porcelain` and the commits on what is
checked out not on its upstream, else not on `origin/HEAD`; it fetches nothing, so `↑` counts
against what the clone last fetched. The line waits for `git` at most 150 ms, and past that shows
the counts it last got in that folder, kept in the plugin's data folder. The version a session
started on is kept there too, by session, at its session start: the line runs through the link the
latest session start points at its own version, so it can't tell the session's from its own.

The counts on the right come from what the last check of the machine's projects found, kept in the
plugin's data folder; the line never runs that check itself, which reads every repo of the last 30
days' Transcripts, but starts it in the background where what it found is over 30 seconds old and no
check runs, so what it shows is at most about a minute old. It leaves out the session it draws for,
which the person is looking at. A session is marked waiting by bagheera's Stop Hook, its
Notification Hook for a permission, and its PreToolUse Hook for `AskUserQuestion`; the mark clears
on the session's next prompt or its end, and the check clears it once the session's Transcript holds
an entry of the person or of Claude after it (Claude Code's own entries after a turn, such as its
Hooks' summary, don't count), or its Claude Code has exited. A headless session is never marked.

It draws its default figures at their default thresholds; no file sets them (PRD no-config). A
plugin can't set Claude Code's `statusLine` itself, and the plugin writes none: each person sets it
in their own `~/.claude/settings.json`, as `python3 -E -s '<plugin data>/bagheera/scripts/run.py'
status-line # managed by bagheera`. The path is a link in `${CLAUDE_PLUGIN_DATA}` that each session
start points at the running version's plugin folder (ADR binary), so the command stays the same from
one version to the next. Where no settings file Claude Code reads sets `statusLine`, the first
session start in a clone has Claude offer the person, once per clone, to add that line, and Claude
adds it only on their yes: to `~/.claude/settings.json` where bagheera is on there, else to the
clone's `.claude/settings.local.json`, where bagheera is on for that clone only (ADR plugin); never
to the committed `.claude/settings.json`, which would choose for the team. A headless session is
told nothing.
## Considered options

- Bars ten cells wide that shrink to five when narrow (until 2026-11-11) — about 150 columns once
  the line counts the sessions waiting and the projects, so a terminal of 120 cut the rest; the
  number already says what the bar shows, and its color says when to look.
- Bars of five cells drawn in eighths, or one cell of eight heights beside the number — closer
  to a bar, but still a column or five each for what the number says.
- The name of the project that waits longest, or of each project, on the right — 16 columns or
  more for what `doctor` lists in full when the count says to look.
- `⟳` for a restart — too like the cache's `↻`; `⇡` with the version says what a restart brings.
- `↓` for the commits behind the upstream — only a fetch knows them, which the line won't run.
- The check run by the line itself — it reads every project's files and runs `git` in each, too
  slow for the 300 ms Claude Code gives a status line.
- A mark cleared when the Transcript is modified after it — Claude Code writes its Hooks' summary
  after the Stop Hook, so every mark would clear at once.

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
- Only telling the person the line to add (until 2026-11-10) — on a clean machine the user set
  the line and the Output style by hand, and asked for them to be added; with their yes, the
  line is still theirs.
- Writing the file that enables the plugin, as the Output style once did — a team's committed
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

- A person who says no sees no line; they are asked once per clone.
- A `statusLine` an earlier Release wrote into a clone's `.claude/settings.local.json` overrides
  the person's own until they remove it; `doctor` names it.
- The line runs the plugin without its Hook's `sh`: before the first session start, after the
  plugin's data folder is removed, or where `python3` is missing or older than 3.9, Claude Code
  shows no line.
- Revisit when Claude Code lets a plugin set a status line of its own.
