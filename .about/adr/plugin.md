# One plugin, `baloo`, in the `bunderlog` marketplace

Date: 2026-09-30

This repo is the `bunderlog` marketplace, and it holds one plugin, `baloo`: skills, Guidelines,
Output styles, hooks and the Go binary the hooks run (ADR binary). The skills always work; each
Check, and each Guideline (ADR guidelines), turns on with a key of its own in the Config, and an
Output style and the Status line with Claude Code's own settings, which the Config's keys set
where none is (ADR output-styles, ADR status-line). The binary's source is in `src/baloo/`,
outside the plugin, so an install doesn't carry it.

Every name the Go code, the binary's and the release tool's, uses for the plugin (its name, folders
and file names) is a constant in `src/baloo/names`, so a rename is one edit in the code, plus the
manifests, the Loader and the docs.

## Considered options

- Two plugins, skills and hooks, each installed on its own — the hooks do nothing useful without
  the skills, and where the binary can't be downloaded the one plugin is already only skills.
- The binary's source inside the plugin, in `plugins/baloo/src/` (until 2026-09-30) — one folder
  for everything a Release ships, but every install carried the Go source, which no user runs.
- The Go module at the repo root, `cmd/` and `internal/` — the usual Go layout, but the root is
  the marketplace's, and a second plugin's binary would have no folder of its own.

## Consequences

- One install, one version, one tag for everything.
- Whether a change needs a Release depends on two folders, `plugins/baloo/` and `src/baloo/`;
  the release tool looks at both (ADR releases).
- The Loader is in `scripts/`, not `bin/`: claude.ai and Cowork don't install a plugin with a
  top-level `bin/`, and nothing needs `baloo` on the Bash tool's `PATH`, since a skill can name
  `${CLAUDE_PLUGIN_ROOT}/scripts/loader`.
- Revisit when a second plugin would share the binary.
