# The release tool releases every plugin in the marketplace under one version

2026-11-09

## Symptom

Phase 4 of the move to three plugins (ADR plugin): `mise run release` makes one Release of all the
marketplace's plugins, one version, one tag and one `CHANGELOG.md` with a section per plugin. Now,
because no plugin can be split out of baloo before a Release can carry it.

## Evidence

- `src/release/release.py` makes a Release of baloo alone and imports `baloo.names`.
- `CLAUDE.md`: a Release "only counts commits under `plugins/baloo/`" (ADR releases).

## Acceptance criteria

- With a second, empty plugin under `plugins/`, `mise run release` runs to a tag on a trial branch.
- PRD harness: "At each Release tag, every plugin's `plugin.json` and its entry in the marketplace
  carry the same version" holds.
- A commit under any `plugins/<name>/`, a schema aside, counts toward a Release, under that
  plugin's section of `CHANGELOG.md`.
- ADR releases states the new rule.

## Comments

### 2026-11-09 · fix option

Keep the tag `v<version>`, or tag each plugin `<plugin>--v<version>` too: Claude Code resolves a
plugin's `dependencies` against the second form (the Inbox's survey of 2026-10-14), which nothing
here uses yet, so `v*` alone is enough until a plugin depends on another.
