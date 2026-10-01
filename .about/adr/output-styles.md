# How Claude replies is an Output style, which session start picks where none is

Date: 2026-10-01

The plugin ships how Claude writes its replies, such as `short-replies`, as Output styles in
`plugins/baloo/output-styles/`, each with `keep-coding-instructions: true` so Claude Code keeps its
own instructions for coding. Claude Code sends the active one with every request, and its own
`outputStyle` setting picks it (`baloo:short-replies`).

The Config's `output-style` key names the plugin's Output style for the repo, and a new Config
names `short-replies`. At session start the binary sets `outputStyle` to it, but not in a Session
review's session (ADR session-review), and only where both hold:
- the plugin is enabled in the project's local or project settings, or the user's: the most
  specific of them that names `baloo@bunderlog` in `enabledPlugins` decides, as in Claude Code;
- none of Claude Code's settings files, managed ones included, sets `outputStyle`, to any value,
  `default` too.

It writes the settings file that enables the plugin, so the style reaches whoever the plugin
does: the project's `.claude/settings.json` for its team, its `.claude/settings.local.json` for
one person, and that `.claude/settings.local.json` too for the user's settings, since the Config
is the repo's and the user's own folder is Claude Code's (ADR config). A `settings.local.json` the
binary creates goes into the repo's `info/exclude`; a file that was there keeps the rest of its
text as it was. `output-style: false` picks none. A plugin can't set a default Output style of its
own, so the binary writes Claude Code's setting.

## Considered options

- A Guideline printed whole at session start, with a key in the Config (until 2026-09-30) — the
  plugin's own switch, but it reaches Claude once, as a Hook's output, and fades over a long
  session.
- Leaving the pick to the user, with no key in the Config (until 2026-09-30) — the binary never
  writes Claude Code's settings, but a new user gets no Output style until they know to choose
  one.
- Picking it in the user's `~/.claude/settings.json` where the plugin is enabled there — one pick
  for every project and outside a repo, but it writes in Claude Code's own folder (ADR config).
- Always picking it in `.claude/settings.local.json` (until 2026-09-30) — a team that enables the
  plugin in the project's settings would get the style one person at a time.
- Stopping only at an `outputStyle` that is set, with no key — Claude Code may record Default by
  removing the setting, and then the binary would pick the style again at every session start.
- Picking it wherever the binary runs — a session with `--plugin-dir`, or with the plugin
  enabled by managed settings, would get it too.
- `force-for-plugin` — every user of the plugin would get the style, with no way to turn it off
  but removing the plugin.
- A plugin's own CLAUDE.md — Claude Code never loads one.

## Consequences

- Only one Output style is active at a time: picking another, such as Explanatory, turns
  `short-replies` off, and the binary leaves that choice alone.
- It picks the style once per project, at a session start: the session may get it only from its
  next request, or its next session.
- A repo whose Config was made before the key has no `output-style`, so nothing is picked there
  until its user adds the key.
- Where the project's `.claude/settings.json` enables the plugin, the pick changes a committed
  file: a diff to commit, and the style for everyone on the team.
- The binary edits a file Claude Code writes too. It replaces the file whole, so neither leaves
  half of it, but if both write it at the same moment, one write is lost.
- Picking Default in `/output-style` may not hold where the Config still names the style, so
  Claude tells the user to set `output-style: false` as well.
- Revisit when Claude Code lets a plugin set a default Output style a user can turn off, or
  allows more than one at a time.
