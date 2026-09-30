# baloo glossary

`baloo`, a Claude Code plugin in the `bunderlog` marketplace: skills that keep a project's
language, decisions and requirements explicit, and hooks run by one Go binary.

## Distribution

**Release**:
A version of the plugin reaching its users: a tagged commit with the new version in
`plugin.json` and its section in `CHANGELOG.md`. Installed copies update only to a new Release, so
a change made without one reaches nobody.
_Avoid_: deploy, publish; "Release" for the GitHub Release
_In code_: `src/release`

**GitHub Release**:
The page on GitHub for a Release's tag, holding its binaries and their `SHA256SUMS` for the
Loader to download.
_Avoid_: "Release" alone

**Loader**:
The plugin's `sh` script, `scripts/loader`, that downloads this machine's binary into the plugin's
data folder, checks its sha256, and runs it.
_Avoid_: installer, bootstrap

## Hooks

**Hook**:
A command Claude Code runs at an event in a session, such as `SessionStart` or `PreToolUse`.
_Avoid_: "hook" for a Git hook

**Git hook**:
A script git runs at a point in its own workflow (`pre-commit`, `commit-msg`, `pre-push`), for
every commit or push, whether or not Claude made it.
_Avoid_: "hook" alone

**Guard**:
The plugin's Hook that stops a tool call before it runs when it would destroy work or leak a
secret into Claude's context, denying it or asking the user first. A guard against accidents,
not a security boundary.
_Planned_: not built yet

**Built-in check**:
A check the binary ships for a Git hook or a project's CI to run, such as `baloo:no-secrets`.
_Avoid_: "check" for one of the Guard's rules
_Planned_: not built yet

**Status line**:
The line Claude Code shows under the prompt; the plugin's own is drawn by the binary.
_Avoid_: "status" alone, which is an ADR's or a PRD's Status
_Planned_: not built yet
