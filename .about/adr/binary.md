# The hooks are one Go binary, downloaded at session start and checked against a sha256 in git

Date: 2026-09-29

The hooks, the Built-in checks and the Status line are one Go binary, `baloo`, with a subcommand
each, so a user's machine needs no runtime. The Release workflow builds it for macOS and Linux,
amd64 and arm64, and attaches each Build, as a bare file, to the GitHub Release.

The Loader, `scripts/baloo`, is a POSIX `sh` script. A `SessionStart` hook runs `baloo install`: it
picks this machine's Build from `scripts/SHA256SUMS`, downloads it from the GitHub Release into
`${CLAUDE_PLUGIN_DATA}` when it isn't there, checks its sha256 against the file, and moves it into
place in one step; a Build already there is checked the same way, once a session. `baloo <args>`
runs that Build. A failure says why on stderr and exits 2, which a `SessionStart` hook shows to the
user.

The sha256 come from git, not from the GitHub Release: the release tool (ADR releases) builds every
platform and commits their sha256 with the new version, and the Release workflow rebuilds from the
tag and publishes only Builds with the same sha256. The build is reproducible to make this work: no
cgo, `-trimpath`, no VCS stamp, the Go version from `go.mod`, and every other setting that changes
the output fixed in `internal/release`. CI builds on Linux and on macOS on every push and fails when
their sha256 differ.

## Considered options

- TypeScript run with `bun` — `bun` would have to be on every machine, or every hook would
  silently do nothing, the Guard too.
- `SHA256SUMS` published with the GitHub Release, as GoReleaser does — whoever can change the
  GitHub Release can change both the Build and its sha256.
- Builds signed with a key, such as cosign or minisign — the key is one more secret to keep, and
  checking a signature needs a tool on the user's machine.
- The plugin as a ZIP with every platform — every user downloads every platform.
- A ZIP per platform through a `command` source — the command runs at every session start, in
  effect `curl … | sh`.
- Builds committed to git — history that grows by every platform's Build with every Release.
- Archives (`.tar.gz`) — about half the download, for `tar` and one more step in the Loader;
  a Build is under 2 MB.

## Consequences

- A user's machine needs `sh`, `curl` or `wget`, and `sha256sum` or `shasum`; macOS and WSL have
  them. There is no Windows Build; Git Bash on Windows gets "no build" at every session start.
- The first session after an install or update waits for the download. Offline, or when the
  download or its check fails, the hooks don't run that session; the parts that must not skip
  silently, such as the Guard, say so (decided with each part).
- `BALOO_RELEASES` points the Loader at another host, which is how the tests serve it a Build;
  the sha256 check still applies, so it can't swap the Build.
- Builds of other versions are deleted from `${CLAUDE_PLUGIN_DATA}` a week after they were
  downloaded, so a session still on an older version keeps its Build meanwhile.
- A change to the Go version is a change to every Build: it needs a Release like any other.
- Revisit when the download fails often enough to matter, or a team needs an offline install.
