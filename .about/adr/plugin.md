# One plugin, `baloo`, in the `bunderlog` marketplace

Date: 2026-09-29

This repo is the `bunderlog` marketplace, and it holds one plugin, `baloo`: skills, hooks and the
Go binary the hooks run (ADR binary). The skills always work; each hook, the Guard among them,
turns on with a key of its own in the config. The binary's source is inside the plugin, in
`plugins/baloo/src/`, since the binary belongs to the plugin and changes with it.

Every name the binary's code knows the plugin by (the plugin, its binary and builds, their paths)
is a constant in `internal/names`, so a rename is one edit there, plus the manifests, the Loader
and the docs.

## Considered options

- Two plugins, skills and hooks, each installed on its own — the hooks do nothing useful without
  the skills, and where the binary can't be downloaded the one plugin is already only skills.
- The binary's source at the repo root, `cmd/` and `internal/` — the usual Go layout, but it
  splits the plugin between two places, and whether a change needs a Release depends on both.

## Consequences

- One install, one version, one tag for everything.
- The plugin as installed carries its binary's Go source, some tens of KB.
- The Loader is in `scripts/`, not `bin/`: claude.ai and Cowork don't install a plugin with a
  top-level `bin/`, and nothing needs `baloo` on the Bash tool's `PATH`, since a skill can name
  `${CLAUDE_PLUGIN_ROOT}/scripts/baloo`.
- Revisit when a second plugin would share the binary.
