# Changelog

The baloo plugin's Releases, newest first.

## 0.10.0 — 2026-10-01

### Features

- guidelines: defer to the codebase's conventions; rules for async, reactivity, stale data (5f346cc)
- guidelines: add a tailwind Guideline, on where the repo depends on tailwindcss (30bec04)
- retro: move workarounds kept in auto-memory into the skills and settings they patch (e3858c4)
- guidelines: tell Claude the rules zsh needs where the Bash tool runs zsh (d956864)
- format-on-edit: run the project's formatter on each file Claude edits (4bc1678)

### Fixes

- loader: never block a prompt or the end of a turn when the binary is missing or fails (ffd6c2e)
- loader: keep a session's binary while only its quiet hooks run it (dab1b0c)
- checks: let no-secrets-in-context pass env piped into a filter that keeps only the names (06b8900)
- checks: read a here-document's body as text, not commands, unless a shell runs it (e9da588)

## 0.9.0 — 2026-10-01

### Features

- config: group the Checks' keys under claude-hooks and git-hooks, for what runs them (a9a4e5e)
- checks: name the setting that makes git pull rebase when linear-history fails (779c0fe)
- git-hooks: write the Git hooks that run the Checks the Config turns on, with husky 9 too (a6d27ba)
- stop-check: run the Config's command when Claude ends a turn that changed the working tree (1e0ab04)

### Fixes

- config: say that the Checks on Claude's tool calls are on without their key (2932918)

## 0.8.0 — 2026-10-01

### Features

- guidelines: add debugging (7bf923c)
- checks: ask before a tool call that may turn the Hooks off (0e1239c)

## 0.7.0 — 2026-10-01

### Features

- checks: reject an accepted ADR changed without today's Date (bc6dfec)
- retro: review past sessions for stalls and the setup changes that would spare them (4fe6687)
- session-review: record what a closed session settled but nobody wrote down (1a0a623)

## 0.6.0 — 2026-10-01

### Features

- checks: reject an AI co-author or credit in a commit message (ad91efe)
- checks: check that a commit message is a Conventional Commit (d32a66c)
- checks: reject secrets and env files in the staged changes (73f8185)
- checks: reject merge commits in a push (b91957b)
- checks: deny a Bash command that bypasses the Git hooks (029c9b1)
- checks: deny a Bash command that destroys work beyond undo (87d058d)
- checks: deny a tool call that would show a secret to Claude (f7ea750)
- checks: turn each Check on or off in the Config, and run them on Claude's tool calls (3c17b0f)

### Fixes

- status-line: keep the Status line when the Config's key can't be read (9fcc5ed)
- status-line: give way to a status line the team sets later (16ba040)
- status-line: show the line when a field has an unexpected type (84fb02b)

## 0.5.0 — 2026-09-30

### Features

- status-line: show the branch, usage bars and model under the prompt (44d3c4e)

## 0.4.0 — 2026-09-30

### Features

- guidelines: name the Guidelines the Config turns on at session start (b5f2e6d)

### Fixes

- output-style: offer more help only when it is needed (240d58f)

## 0.3.0 — 2026-09-30

### Features

- output-style: pick short-replies at session start where no style is set (8443562)

## 0.2.0 — 2026-09-30

### Features

- skills: add the adr, architecture, ask, glossary, prd and tidy skills (b438905)
- config: create .claude/baloo.yml at session start (3286a95)

## 0.1.0 — 2026-09-29

### Features

- scaffold the baloo plugin with a downloaded Go binary (02087b0)
