# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins. It holds one plugin, `baloo`, described in
its [plugin.json](plugins/baloo/.claude-plugin/plugin.json).

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install baloo@bunderlog
```

Why things are the way they are is in [.about/adr/](.about/adr/).

## Development

This repo uses its own plugin: `.claude/settings.json` installs `baloo` from GitHub, so a session
here runs its last Release. To try an edit to a skill or hook before a Release, start a session
with `claude --plugin-dir plugins/baloo`; the binary is still the last Release's. Its source is in
`src/baloo/`, and `mise run check` formats, vets and tests it. To make a Release, run
`mise run release` and push it with `git push --follow-tags`.
