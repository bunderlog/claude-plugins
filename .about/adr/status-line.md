# The Status line is the binary's, set by session start in the project's local settings

Date: 2026-10-04

The plugin ships a Status line: the branch on the left, the context, 5-hour and 7-day Usage bars
and the Cache bar centered, the Cache bar last since nothing in parentheses closes it, and the
model with its effort on the right. The binary draws it, `baloo status-line`, from what Claude
Code gives a status line command on stdin; a line too narrow shrinks the bars, then drops the
reset times, the 5-hour's clock time and the 7-day's weekday, then the model. Each Usage bar turns
yellow and red at percentages, by default the context at 15 and 20, the 5-hour at 70 and 85, the
7-day at 80 and 95.

The Cache bar reads Claude Code's `prompt_cache`: it fills with the share of the cache's lifetime
left, 5 minutes or an hour, turning yellow below 40% and red below 20% by default, and empty when
cold; beside it are the minutes until the cache goes cold, rounded up, or `cold` in red. Without
the context bar the cache's size follows them, the tokens the next message writes again once it
is cold; it is the context's tokens again, so beside them it would say the same twice. With
caching off it doesn't show. Claude Code runs the line again when the cache goes cold, and the
`statusLine` setting asks it to every 60 seconds besides, so the minutes count down while idle.

The Config's `status-line` key turns it on, and a new Config has it on. Instead of `true` it takes
`bars`, the bars shown in their order, and `thresholds`, each bar's `yellow` and `red`; one it
leaves out keeps its default, and a wrong one is a problem at session start that keeps its default.
The binary reads them from the Config each time it draws the line, so an edit shows at the next
run, not the next session.

A plugin can't set Claude Code's `statusLine` itself, so at session start the binary writes it, as
it picks an Output style (ADR output-styles) and not in a Session review's session, where both
hold:
- the plugin is enabled in the project's local or project settings, or the user's;
- none of the project's local or project settings, nor the managed ones, sets `statusLine`: the
  user's own, for every project, gives way to the repo's key.

Once the plugin's is set, one that the project or managed settings set later wins: the binary
takes the plugin's out.

It always writes the project's `.claude/settings.local.json`, whichever file enables the plugin,
since the command names a path on one machine: `'<plugin data>/baloo' status-line # managed by
baloo`. The path is a link in `${CLAUDE_PLUGIN_DATA}` that each session start points at the binary
running it, so the command stays the same from one version to the next; the comment marks it as
the plugin's, which the binary sets again when its path changes and takes out with
`status-line: false`. A Config without the key, or with a value that is wrong, leaves the line as
it is, so a typo in the Config never takes it out. A `settings.local.json` it creates goes into
the repo's `info/exclude`, and one that was there keeps the rest of its text as it was.

## Considered options

- Giving way, as the Output style does, to a `statusLine` in any settings file — a user with a
  status line of their own for every project would never get the plugin's.
- One list of bars, each a name or a name with its thresholds — shorter, but its
  entries mix two types, which a schema and an editor handle worse.
- Writing the bars into the command's arguments at session start — an edit shows only in the
  next session.
- Writing the file that enables the plugin, as the Output style does — a team's committed
  `.claude/settings.json` would get a path from one person's machine.
- The Loader's path in the installed plugin, rewritten at each session start — the path changes
  with every version, so each update rewrites the settings file, and the line breaks in the
  sessions between the update and the rewrite.

- A countdown in seconds, run every second — a binary and a `git` call each second for a number
  nobody reads to the second.
- The cache's hit ratio, as the prompt-cache-control mod shows it, as the bar or beside it — over
  a session it stays near 98% and says nothing; the time left is what tells whether to send the
  next message now or `/compact` first.
- The last miss's cause beside it for a while after a miss — it seldom tells what to do.

## Consequences

- In a repo whose Config has it on, the plugin's Status line replaces the user's own.
- The binary sets it at a session start, after Claude Code has read the settings, so the first
  session may show it only from its next message.
- A repo whose Config was made before the key has no `status-line`, so the Status line stays off
  there until its user adds the key.
- The line runs the binary without the Loader: before the first download, or after the plugin's
  data folder is removed, the command fails and Claude Code shows no line.
- Revisit when Claude Code lets a plugin set a status line of its own.
