# The Config is `.claude/baloo.yml`, created at session start with every Check on

Date: 2026-09-30

A repo's settings for the plugin are one file, `.claude/baloo.yml`, beside Claude Code's own
settings in the root of its repo: the nearest folder up from the project that holds a `.git`, found
without running git. Each Check turns on with a key of its own (ADR plugin), and without it is off.

At session start the binary creates the Config in a repo that has none, with every Check on, and
tells Claude to tell the user; a repo turns a Check off by editing its key. Outside a repo, when
the repo is the home folder itself, a dotfiles repo, or when it is Claude Code's own folder,
`$CLAUDE_CONFIG_DIR` or `~/.claude/`, or inside it, such as a marketplace Claude Code cloned, it
neither creates nor reads a Config and every setting has its default, so Claude Code's own
`.claude/` is never taken for one, and nothing is written in Claude Code's own folder. A new
Config's first line names the JSON Schema, `plugins/baloo/schema.json` on `main`, for editors, and
its comments say how the settings work. A Config that is there is never written to.

The binary reads it with `go.yaml.in/yaml/v3`, the YAML organization's maintained copy of
`gopkg.in/yaml.v3`, and goes through its top-level keys itself. A key that isn't a setting, or a
value that doesn't decode, is a problem, one line with its line number, and that setting keeps
its default while the others apply; a file that isn't YAML or isn't a map of settings is one
problem, and none of it applies. At session start the SessionStart hook prints, for Claude, only a
Config it created and the problems.

## Considered options

- Creating it only when asked, by an `init` skill, with every Check off (until 2026-09-30) —
  nothing appears in a repo nobody set up, but a repo gets no Check until someone knows to ask
  for the Config.
- Creating it at session start only where the project's own `.claude/settings.json` enables the
  plugin — a user-scope install would get no Check anywhere without a step of its own.
- An `init` command that also downloads the binary and writes the hooks into the project's
  `.claude/settings.json` — nothing would run without asking, but project settings have no
  `${CLAUDE_PLUGIN_ROOT}`, so the binary would need a path of its own outside the plugin, and a
  plugin update would need `init` again.
- JSON with comments, or the same keys in either format — a parser or an editing step of our own
  for each format.
- `gopkg.in/yaml.v3` — archived, so a fix would never come.
- `goccy/go-yaml` — better error messages, but a bigger API and more code in the binary.
- Decoding the whole file with `KnownFields` — the problems would be the library's messages,
  which name Go types.
- `.baloo.yml` at the repo's root (until 2026-09-30) — one more file at the root, apart from the
  `.claude/settings.json` that enables the plugin.
- Finding the root with `git rev-parse` — a process on every hook that reads the Config.

## Consequences

- With a user-scope install, every repo opened gets a Config, and every Check, at its first
  session: a new file to commit, and Checks such as Git hooks and commit rules it didn't ask for.
- A deleted Config comes back at the next session start; a repo opts out of a Check by turning
  its key off, not by deleting the file.
- Every new key needs a field in `Config`, an entry in `keys` and in the schema (a test checks
  the two agree), and the key, turned on, in the template.
- A new key reaches a Config that exists only when its user adds it, so its default must be what
  the Check did before it had the key.
- The schema is read from `main`, so an editor can check a Config against settings newer than
  the installed Release.
- The path says Claude, though the Checks Git hooks run act on every commit, Claude's or not.
- Only the first YAML document is read; a second one is ignored silently.
- Revisit when a repo the plugin reaches gets Checks nobody asked for, a repo needs settings that
  differ per folder, or one Config for many repos.
