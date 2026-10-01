# The Status line is the binary's, set by session start in the project's local settings

Date: 2026-10-01

The plugin ships a Status line: the branch on the left, the context, 5-hour and 7-day Usage bars
centered, and the model with its effort on the right. The binary draws it, `baloo status-line`, from
what Claude Code gives a status line command on stdin; a line too narrow shrinks the bars, then
drops the 5-hour reset time, then the model. Each bar turns yellow and red at fixed percentages:
the context at 15 and 20, the 5-hour at 70 and 85, the 7-day at 80 and 95.

The Config's `status-line` key turns it on, and a new Config has it on. A plugin can't set
Claude Code's `statusLine` itself, so at session start the binary writes it, as it picks an Output
style (ADR output-styles) and not in a Session review's session, where both hold:
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
- Thresholds for each bar in the Config — an object where `true` is, for settings nobody has
  changed yet; they can come later without breaking a Config.
- Writing the file that enables the plugin, as the Output style does — a team's committed
  `.claude/settings.json` would get a path from one person's machine.
- The Loader's path in the installed plugin, rewritten at each session start — the path changes
  with every version, so each update rewrites the settings file, and the line breaks in the
  sessions between the update and the rewrite.

## Consequences

- In a repo whose Config has it on, the plugin's Status line replaces the user's own.
- The binary sets it at a session start, after Claude Code has read the settings, so the first
  session may show it only from its next message.
- A repo whose Config was made before the key has no `status-line`, so the Status line stays off
  there until its user adds the key.
- The line runs the binary without the Loader: before the first download, or after the plugin's
  data folder is removed, the command fails and Claude Code shows no line.
- Revisit when Claude Code lets a plugin set a status line of its own.
