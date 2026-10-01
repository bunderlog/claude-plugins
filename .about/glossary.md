# baloo glossary

`baloo`, a Claude Code plugin in the `bunderlog` marketplace: skills that keep a project's
language, decisions and requirements explicit or run a Retro; a Session review; Guidelines of
working rules; Checks in one Go binary that Hooks and Git hooks trigger; an Output style for
Claude's replies; and a Status line.

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
_Planned_: the plugin writing, at session start, the Git hooks that the Git hook Checks the Config
turns on run in

**Config**:
A repo's settings for the plugin, `.claude/baloo.yml` from its root, created at its first session
start with every Check on and the Guidelines that fit the repo. Each Check and each Guideline
turns on with a key of its own there; a wrong setting is reported at session start, and its
default applies.
_Avoid_: settings, which are Claude Code's `settings.json`
_In code_: `src/baloo/internal/config`

**Check**:
Code in the binary that a Hook or a Git hook triggers, such as `baloo:no-secrets-in-commits`,
turned on or off by a key of its own in the Config. Each runs either in a Hook or in a Git hook,
called "a Check a Hook runs" and "a Check a Git hook runs" (for short, "a Hook Check" and "a Git
hook Check").
_Avoid_: built-in check; "a Check on Claude's tool calls"
_In code_: `src/baloo/internal/checks`; `HookChecks`, `GitHookChecks`

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
The line Claude Code shows under the prompt; the plugin's own, with the branch, the Usage bars and
the model, is drawn by the binary, and set in the project's local settings where the Config turns
it on.
_Avoid_: "status" alone, which is an ADR's or a PRD's Status
_In code_: `src/baloo/internal/statusline`

**Usage bar**:
One of the Status line's three bars showing how much is used: the context window, and the 5-hour
and 7-day rate limits.
_Avoid_: meter, gauge

## Secrets

**Secret**:
A value that grants access: an API key, token, password or private key. A placeholder, a
published example or a key meant to be public (a Stripe publishable key, a Firebase web key)
isn't one, even where a Check can't tell the difference. An Env file counts as holding Secrets
unless its first line says it holds none.
_Avoid_: credential, key (alone)

**Env file**:
A file of environment settings a program or shell loads: `.env`, `.env.local`, `prod.env`,
direnv's `.envrc`… A template of one (`.env.example`, `.sample`, `.template`, `.dist`) isn't one.

**Leak**:
A Secret reaching anyone or anywhere it wasn't meant for: a commit, Claude's context, another
host.

## Sessions

**Setup**:
Everything that shapes how Claude works in a project: its CLAUDE.md, the Config, Claude Code's
settings, and the skills, Hooks and plugins it uses.
_Avoid_: harness

**Transcript**:
The record Claude Code keeps of a session: every prompt, reply and tool call, with the call's full
output, so it can hold a Secret a Check missed.
_Avoid_: log, history

**Retro**:
A review the user asks for of how past sessions went: their Stalls, and the change to the Setup
that would have spared each. It looks at how the work went, not at what it produced.
_Avoid_: retrospective, post-mortem
_In code_: the `retro` skill; `src/baloo/internal/condense`

**Stall**:
A point in a session that cost the user something the Setup could have spared: a failed or
refused tool call, an interrupt, a correction, a prompt the user types again and again. A red test
mid-change, a denial that was right, or a call that is the user's to make each time isn't one.
_Avoid_: issue, incident

**Session review**:
A review the plugin starts itself when a session ends, where the Config turns it on: a separate
headless session records in the glossary and the ADRs what the conversation settled but nobody
wrote down, and the next session start says what it changed. Unlike a Retro, it looks at what was
settled, not at how the work went.
_Avoid_: session-end review
_In code_: `src/baloo/internal/review`
