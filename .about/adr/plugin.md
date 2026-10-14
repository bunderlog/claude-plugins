# One plugin, `baloo`, in the `bunderlog` marketplace

Date: 2026-10-14

This repo is the `bunderlog` marketplace, and it holds one plugin, `baloo`: skills, an agent
(ADR verify), Guidelines, Output styles, Hooks and the Python code they run, which ships inside
the plugin (ADR binary). The skills and the agent always work; each Check, and each Guideline (ADR
guidelines), turns on with a key of its own in the Config, and an Output style and the Status line
with Claude Code's own settings, which the Config's keys set where none is (ADR output-styles, ADR
status-line).

Every name the code, the plugin's and the release tool's, uses for the plugin (its name, folders
and file names) is a constant in one module, so a rename is one edit in the code, plus the
manifests and the docs.

New work that leans on what baloo already has is part of baloo, not a plugin of its own: fixing a
failed CI run is the `ci` Guideline (ADR guidelines), which follows `debugging` and hands a flaky
failure to the `issue` skill, and a second plugin would need its own tags, CHANGELOG and Releases
(ADR releases) to read baloo's files anyway.

## Considered options

- Two plugins, skills and Hooks, each installed on its own — the Hooks do nothing useful without
  the skills, and where `python3` is missing the one plugin is already only skills.
- A plugin per role on top of baloo, which would keep only the project's knowledge: `bagheera`
  for developers, `kaa` for testers, `hathi` guarding with the Checks and Git hooks, `mowgli` for
  the person's own setup, `akela` for product managers (agreed in an interview 2026-10-05, never
  built; dropped 2026-10-07) — it rested on enforcement in code being a niche of its own, which
  the measurement didn't confirm (ADR measurement): what is left beside the knowledge is too
  little to split.
- A second plugin for fixing a failed CI run — installed without baloo, but it would find the
  local command to reproduce a failure on its own, and the release tool, tags and CHANGELOG
  would have to handle two plugins.

## Consequences

- One install, one version, one tag for everything.
- Whether a change needs a Release depends on one folder, `plugins/baloo/` (ADR releases).
- The entry script is in `scripts/`, not `bin/`: claude.ai and Cowork don't install a plugin with
  a top-level `bin/`, and nothing needs `baloo` on the Bash tool's `PATH`, since a skill can name
  its path under `${CLAUDE_PLUGIN_ROOT}/scripts/`.
- Revisit when a second plugin would share the code, or when work is wanted without baloo's
  Hooks and Guidelines.
