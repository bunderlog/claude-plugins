# The hooks run one Go binary, downloaded at session start from its GitHub Release

Date: 2026-09-30

Claude Code's Hooks and Git hooks are only triggers: each runs one Go binary, `baloo`, which runs
the Checks the Config turns on (ADR config). The Checks and the Status line are the binary's code,
so a user's machine needs no runtime.

The Loader, `scripts/loader`, is a POSIX `sh` script. The `SessionStart` hook runs the Loader's
`session-start`, which runs the binary's `session-start` once this machine has the binary of the
version in `plugin.json`. It downloads one only when it is missing, or no longer has the sha256 it
was downloaded with, kept beside it and checked once a session: it downloads the GitHub Release's
`SHA256SUMS` and this machine's binary into `${CLAUDE_PLUGIN_DATA}`, checks the binary's sha256
against the file, and moves it into place in one step. `loader <args>` runs the binary. A failure
says why on stderr and exits 2, which a `SessionStart` hook shows to the user.

The Release workflow builds the binary from the tag for macOS and Linux, amd64 and arm64, and
publishes each platform's, as a bare file named like `baloo_0.1.0_darwin_arm64`, with their
`SHA256SUMS` on the GitHub Release (ADR releases). The sha256 check catches a download that was cut
short or damaged.

## Considered options

- TypeScript run with `bun` — `bun` would have to be on every machine, or every Check would
  silently do nothing.
- The sha256 committed to the repo with each Release, and the Release workflow publishing only
  binaries it rebuilds to the same sha256 (until 2026-09-30) — a replaced GitHub Release would be
  caught, but every Release needed a reproducible build on the releasing machine and in CI, and a
  commit of the sha256, for a risk this plugin doesn't carry.
- Binaries signed with a key, such as cosign or minisign — the key is one more secret to keep, and
  checking a signature needs a tool on the user's machine.
- The plugin as a ZIP with every platform — every user downloads every platform.
- A ZIP per platform through a `command` source — the command runs at every session start, in
  effect `curl … | sh`.
- Binaries committed to git — history that grows by every platform's binary with every Release.
- Archives (`.tar.gz`) — about half the download, for `tar` and one more step in the Loader;
  a binary is under 2 MB.

## Consequences

- A user's machine needs `sh`, `curl` or `wget`, and `sha256sum` or `shasum`; macOS and WSL have
  them. There is no Windows binary; Git Bash on Windows gets "no binary" at every session start.
- The first session after an install or update waits for the download. Offline, or when the
  download or its check fails, no Check runs that session; the Checks that must not skip
  silently say so (decided with each).
- `BALOO_RELEASES` points the Loader at another host, which is how the tests serve it a Release.
- Binaries of other versions are deleted from `${CLAUDE_PLUGIN_DATA}` a week after they were last
  run, so a session still on an older version keeps its binary meanwhile.
- A change to the Go version is a change to every binary: it needs a Release like any other.
- Revisit when the download fails often enough to matter, a team needs an offline install, or
  the plugin reaches users for whom a replaced GitHub Release is a risk worth the extra steps.
