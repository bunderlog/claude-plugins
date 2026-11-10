# How Claude replies is an Output style, which each person picks in their own settings

Date: 2026-11-10

The plugin ships how Claude writes its replies, such as `short-replies`, as Output styles in
`plugins/baloo/output-styles/`, each with `keep-coding-instructions: true` so Claude Code keeps its
own instructions for coding. Claude Code sends the active one with every request, and its own
`outputStyle` setting picks it (`baloo:short-replies`).

The plugin picks none: each person picks their own in `~/.claude/settings.json`,
`baloo:short-replies` or any other, since how Claude talks to them is theirs (PRD harness, PRD
no-config). Where no settings file Claude Code reads (the person's, the project's, the clone's local
or the managed ones) sets `outputStyle`, the first session start in a clone tells Claude, to tell
the person, the line to add, once per clone; a headless session is told nothing and leaves the
telling for the next. A plugin can't set a default Output style but by `force-for-plugin`, which
would override the person's own.

## Considered options

- The Config's `output-style` key, which session start wrote into the settings file that enabled
  the plugin where none set one (until 2026-11-10) — a committed `.claude/settings.json` chose for
  the whole team, a clone's local file froze one person's choice, and the Config was a switch of
  its own beside Claude Code's (PRD no-config).
- A Guideline printed whole at session start, with a key in the Config (until 2026-09-30) — the
  plugin's own switch, but it reaches Claude once, as a Hook's output, and fades over a long
  session.
- Leaving the pick to the user, with no key in the Config (until 2026-09-30) — the plugin never
  writes Claude Code's settings, but a new user gets no Output style until they know to choose
  one.
- Picking it in the user's `~/.claude/settings.json` where the plugin is enabled there — one pick
  for every project and outside a repo, but it writes in Claude Code's own folder (ADR config).
- Always picking it in `.claude/settings.local.json` (until 2026-09-30) — a team that enables the
  plugin in the project's settings would get the style one person at a time.
- Stopping only at an `outputStyle` that is set, with no key — Claude Code may record Default by
  removing the setting, and then the plugin would pick the style again at every session start.
- Picking it wherever the plugin runs — a session with `--plugin-dir`, or with the plugin
  enabled by managed settings, would get it too.
- `force-for-plugin` — every user of the plugin would get the style, with no way to turn it off
  but removing the plugin.
- A plugin's own CLAUDE.md — Claude Code never loads one.
- A second, fuller Output style that explains or teaches — Claude Code's own Explanatory and
  Learning styles already do.

## Consequences

- Only one Output style is active at a time: picking another, such as Explanatory, turns
  `short-replies` off.
- A person who never adds the line gets Claude Code's default style; they are told once per clone.
- An `outputStyle` of `baloo:short-replies` an earlier Release wrote into a clone's
  `.claude/settings.local.json` stays until the person removes it; `doctor` names it.
