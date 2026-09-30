# Changelog

The baloo plugin's Releases, newest first.

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
