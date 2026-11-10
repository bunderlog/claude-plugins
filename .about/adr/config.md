# baloo has no Config: all of it is on where Claude Code turns the plugin on

Date: 2026-11-10

baloo reads no settings file of its own and creates none (PRD no-config): its Checks in Hooks, its
Guidelines and the Session review are on in every repo where Claude Code's `enabledPlugins` turns
baloo on, and turning baloo off is the only switch. The Output style and the Status line are each
person's, in their own `~/.claude/settings.json` (ADR output-styles, ADR status-line), and a
project that wants its formatter run on Claude's edits adds its own `PostToolUse` Hook (ADR
format-on-edit). A Hook finds the repo it runs in as the nearest folder up from the project that
holds a `.git`, without running git, and none in the home folder or Claude Code's own folder.

A `.claude/baloo.yml` left in a repo is read by nobody; `doctor` names it for the person to remove.

## Considered options

- The Config, `.claude/baloo.yml`, created at a clone's first session start with every Check on
  and the Guidelines that fit the repo, each part turned on or off by a key of its own, read by
  the plugin's own YAML parser (until 2026-11-10) — a teammate's clone got a Config before anyone
  decided on one, what was on differed from project to project for no reason anyone recorded, and
  about 1,300 lines did nothing but read it and write Claude Code's settings from it.
