# The Hooks and Git hooks run the plugin's own Python code, standard library only

Date: 2026-10-14

Claude Code's Hooks and Git hooks are only triggers: each runs `baloo`, the plugin's Python code,
which runs the Checks the Config turns on (ADR config). The code ships inside the plugin, so what
runs on a user's machine is code they, a reviewer or Claude can read and debug there, and a
Release has nothing to build per platform or to download. It uses Python's standard library only,
so nothing is installed, and supports Python 3.9 and later, the `python3` that Xcode's Command
Line Tools ship and Debian 11 has. Anthropic's own plugins, `hookify` and `security-guidance`, run
`python3` from their Hooks the same way, so it is a requirement plugins already make.

Each Hook runs the plugin's entry script with `python3 -E -s` by `${CLAUDE_PLUGIN_ROOT}`: `-E` and
`-s` keep a user's `PYTHONPATH` and user site from changing what runs, where `-I` would also drop
the script's own folder from the import path. The `SessionStart` Hook first checks, in `sh`, that
`python3` is there and 3.9 or later; when it isn't, it says why on stderr and exits 2, which
Claude Code shows to the user. Every other Hook fails silently instead, since exit 2 there would
stop a tool call, a prompt or a turn's end (ADR guidelines, ADR checks).

In the port, each part session start reports on (the Config, the Output style, the attribution,
the Status line, the Git hooks, the Session review, the Inbox, the Guidelines, the uncommitted
edits in `.about/`) returns its own lines, and session start only gathers them; the Inbox's parsing
is a module of its own. In Go, `sessionStart` wrote every part's lines itself, so each new part
edited `main.go` and its 857-line test. The Go code isn't reshaped first, since the port replaces
it.

The repo, `bunderlog/claude-plugins`, is public, since everything a user's machine fetches from it
must work without a token: the Config's `$schema` from `raw.githubusercontent.com`, and Claude
Code installing and updating the plugin in the background.

## Considered options

- One Go binary, downloaded at session start from its GitHub Release by the `sh` Loader and
  checked against its `SHA256SUMS` (until 2026-10-14) — no runtime on the user's machine and about
  2 ms a start against Python's 7, but the binary was opaque where it ran, and it took a build per
  platform, a Loader, a wait for the download after each update, no Windows, and no Checks offline.
- TypeScript run with `bun` — `bun` would have to be on every machine, where `python3` usually is.
- Python with packages from PyPI — every machine would need an install step and a place for them.
- A private repo, read with a GitHub token — every user would need a token on every machine, set
  where the editor fetching `$schema` and Claude Code's background update each find it.

## Consequences

- A user's machine needs `python3` 3.9 or later on the Hooks' `PATH`; a stock Mac gets it with
  the Command Line Tools, which its first `python3` offers to install. Where it is missing, no
  Check runs that session; the Checks that must not skip silently say so (decided with each).
- The code is written for 3.9: no `match`, no `tomllib`, and newer type syntax only behind
  `from __future__ import annotations`.
- Each Hook starts Python, about 7 ms here against the Go binary's 2, plus its imports.
- The Git hooks and the Status line keep their fixed link in `${CLAUDE_PLUGIN_DATA}`, now to the
  running version's plugin folder (ADR git-hooks, ADR status-line).
- The binaries of Releases before the port stay on GitHub, since copies still on those versions
  download them by their `v*` tag.
- Until the port from Go lands, the Go binary and its Loader still run, and the ADRs and the
  glossary that name them describe them; each is edited as its part moves.
- Windows is untried: it works only where `python3` runs in the shell Claude Code gives Hooks.
- Making the repo private is a one-way door: every installed copy stops updating at once.
  Everything committed, `.about/` included, is public.
- Revisit when Python's start time or the spread of its versions hurts in use, or a Check needs
  what the standard library doesn't have.
