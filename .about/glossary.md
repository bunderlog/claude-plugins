# baloo glossary

`baloo`, a Claude Code plugin in the `bunderlog` marketplace: skills that keep a project's
language, decisions and requirements explicit, Guidelines of working rules, Checks in one Go binary
that hooks trigger, and an Output style for Claude's replies.

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
A script git runs at a step of its own (`pre-commit`, `commit-msg`, `pre-push`), on every commit
or push, whether you or Claude made it.
_Avoid_: "hook" alone

**Config**:
A repo's settings for the plugin, `.claude/baloo.yml` from its root, created at its first session
start with every Check on and the Guidelines that fit the repo. Each Check and each Guideline
turns on with a key of its own there; a wrong setting is reported at session start, and its
default applies.
_Avoid_: settings, which are Claude Code's `settings.json`
_In code_: `src/baloo/internal/config`

**Check**:
Code in the binary that a Hook or a Git hook triggers, such as `baloo:no-secrets`; none runs
until the Config turns it on.
_Avoid_: built-in check
_Planned_: not built yet

**Guideline**:
A file of working rules the plugin ships, for any project (`principles`, `design`) or for one
stack (`go`, `vue`), that Claude reads when a task calls for it; one the Config turns on is named
to Claude at session start.
_Avoid_: rule, guide; a skill, which Claude Code always lists; "Guideline" for an Output style
_In code_: `src/baloo/internal/guidelines`

**Output style**:
Instructions for how Claude writes its replies, such as `short-replies`, that the plugin ships
and Claude Code sends with every request once its own `outputStyle` setting picks one; the
Config names the one to pick where no setting does.
_Avoid_: "style" alone; tone

**Status line**:
The line Claude Code shows under the prompt; the plugin's own is drawn by the binary.
_Avoid_: "status" alone, which is an ADR's or a PRD's Status
_Planned_: not built yet
