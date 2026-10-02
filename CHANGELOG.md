# Changelog

The baloo plugin's Releases, newest first.

## 0.16.0 — 2026-10-02

### Features

- guidelines: answer a question without acting, commit only the task's changes, check each part (94453f1)

## 0.15.1 — 2026-10-02

### Fixes

- checks: see the program after a shell keyword, and let a for loop read the Config (4ab2d49)

## 0.15.0 — 2026-10-02

### Features

- verify: verify a change against the project's decisions with the verifier agent (a1518da)

## 0.14.3 — 2026-10-01

### Fixes

- checks: don't ask before a Bash command that only reads the Config (6b3db33)

## 0.14.2 — 2026-10-01

### Fixes

- retro: say that --around cuts each block at 2,000 characters (05ee900)

## 0.14.1 — 2026-10-01

### Fixes

- retro: charge a call by its text, an image by an estimate; skip Claude Code's own messages (15af2d6)
- session-review: let the review delete .about/inbox.md with its last item (1f8a810)
- issue: write an Inbox item in the Inbox's format; allow the tracker's command-line client (df89942)

## 0.14.0 — 2026-10-01

### Features

- issue: write an Issue to the project's tracker or .about/issues/ with the issue skill (08bbaff)
- tidy: recheck the ADRs' facts against the code and each other (b9bdb19)
- retro: look for expensive calls, by the tokens each added to the context (5e9d881)
- session-start: show the user the plugin's version (27547de)
- guidelines: let a part inside a module keep a seam and tests of its own (890381c)
- stop-check: hand the command the HEAD the turn started from in BALOO_BASE (3a87eb3)
- inbox: delete .about/inbox.md with its last item (49a69b9)
- inbox: go through the Inbox in rounds the user can stop and pick up later (6c7face)

## 0.13.0 — 2026-10-01

### Features

- guidelines: keep a seam inside a module out of its interface (823dc82)
- interview: rename the ask skill to interview (a5ae77c)
- architecture: flag callers relying on what a module doesn't promise; name what's behind a seam (244b5c8)

## 0.12.0 — 2026-10-01

### Features

- retro: look for missing information and unchecked projects, and enforce fixed-pattern mistakes (e928915)
- inbox: keep what is still open in .about/inbox.md, and go through it with the inbox skill (05eb3fd)

### Fixes

- checks: read an ADR's Date in a file with CRLF line endings (03dcf96)

## 0.11.0 — 2026-10-01

### Features

- checks: deny pruning unreachable commits and deleting .git; find JWTs and URL passwords (ae9f83a)
- guidelines: rules for stale builds, measured claims and removing what has consumers (85a996b)
- guidelines: rules for pkill -f, fixing every instance, and the project's own checks (02ab671)
- checks: let git push --delete pass for a branch the remote's default branch holds (795cfa2)
- session-start: turn off Claude Code's commit attribution where no-ai-coauthor is on (efbe90d)

### Fixes

- session-review: change nothing but the glossary and ADRs in the review's own session (2d88127)

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
