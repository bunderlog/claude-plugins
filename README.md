# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins. It holds one plugin, `baloo`, described in
its [plugin.json](plugins/baloo/.claude-plugin/plugin.json).

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install baloo@bunderlog
```

Why things are the way they are is in [.about/adr/](.about/adr/).

## Development

This repo uses its own plugin: `.claude/settings.json` enables `baloo` from the working tree, so
an edit to a skill or hook takes effect at the next session or `/reload-plugins`. The binary is
the last Release's; its source is in `plugins/baloo/src/`, and `mise run check` formats, vets and
tests it. To make a Release, run `mise run release` and push it with `git push --follow-tags`.
