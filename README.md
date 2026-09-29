# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins. It holds one plugin, `baloo`, described in
its [plugin.json](plugins/baloo/.claude-plugin/plugin.json).

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install baloo@bunderlog
```

Why things are the way they are is in [.about/adr/](.about/adr/).

## Development

The binary's source is in `plugins/baloo/src/`; `mise run check` formats, vets and tests it.
To try the plugin from a checkout, run `claude --plugin-dir plugins/baloo`; it downloads the
binary of the last Release. To make a Release, run `mise run release` and push it with
`git push --follow-tags`.
