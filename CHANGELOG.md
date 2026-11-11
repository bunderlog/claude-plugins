# Changelog

The marketplace's Releases, newest first.

## 0.57.0 — 2026-11-11

### bagheera

#### Features

- bagheera: show the latest 5-hour and 7-day limits any session got in the Status line (ca1439a)

## 0.56.0 — 2026-11-11

### bagheera

#### Features

- bagheera: show the project's folder light cyan and the branch light blue in the Status line (d7afc37)

## 0.55.0 — 2026-11-11

### bagheera

#### Features

- bagheera: show uncommitted and unpushed work and a restart's version in the Status line (0c90715)

## 0.54.0 — 2026-11-11

### bagheera

#### Features

- bagheera: show sessions waiting and projects needing attention in the Status line and doctor (ef8cdb4)

## 0.53.0 — 2026-11-11

### bagheera

#### Features

- bagheera: set a repo up in one step with /bagheera:setup, and name what it lacks in doctor (f252fd3)
- bagheera: offer each person deny rules that keep Secrets' files out of every session (d2b0514)

## 0.52.0 — 2026-11-10

### baloo

#### Features

- baloo: name every ADR, PRD, Issue and term of the project at session start (2542bc0)

## 0.51.1 — 2026-11-10

### louie

#### Fixes

- louie: have the go-vue template's test helper take t and mark itself a helper (f49d35e)
- louie: answer an unknown path or method of the go-vue template's API with respond's JSON (fc98a4e)
- louie: open the go-vue template's database from sqlc's internal/db, not a second package (ec889da)
- louie: stop the go-vue template's CLAUDE.md restating setup and asking for check before a push (cfe4c7a)
- louie: open each of the go-vue template's .vue files with a comment saying what it is (f8b9a01)

## 0.51.0 — 2026-11-10

### louie

#### Features

- louie: deliver up to five Issues at once, all planned before any is built (49e157e)

## 0.50.0 — 2026-11-10

### bagheera

#### Features

- bagheera: offer to add its Status line and Output style, and add them on a yes (681ec6e)

#### Fixes

- bagheera: refuse the simple variants of a Git hook bypass (883e103)
- bagheera: refuse showing an env file through a pattern or an inline script (ce17c44)
- bagheera: quote the Session review's decision command for any path (5d116a5)

### louie

#### Fixes

- bagheera: refuse the simple variants of a Git hook bypass (883e103)

## 0.49.1 — 2026-11-10

### louie

#### Fixes

- louie: log the go-vue template's failed response writes with the request's context (73468ff)

## 0.49.0 — 2026-11-10

### louie

#### Features

- louie: run the go-vue template with mise run dev and deploy it with Kamal (4e07a46)

## 0.48.0 — 2026-11-10

### louie

#### Features

- louie: give the go-vue template apps/app, a Vue app in a pnpm workspace (c101f4f)

## 0.47.0 — 2026-11-10

### louie

#### Features

- louie: give the go-vue template apps/api, a Go module serving GET /api/up (ab6cece)

## 0.46.0 — 2026-11-10

### louie

#### Features

- louie: add /louie:new, which starts a Go and Vue product from the go-vue template (66938fd)

## 0.45.1 — 2026-11-10

### louie

#### Fixes

- deliver: stop only on the Issue's own decisions, and leave no empty worktree (097c5ea)

## 0.45.0 — 2026-11-10

### louie

#### Features

- louie: add /louie:deliver, which takes an agreed Issue to a pull request (8d84920)

## 0.44.1 — 2026-11-10

### bagheera

#### Fixes

- session-start: tell once to pick bagheera:short-replies where baloo's is still set (a35936f)
- retro: count an earlier baloo's Check denials as Checks (2a4f2e3)

## 0.44.0 — 2026-11-10

### louie

#### Features

- louie: add /louie:plan, which plans an agreed Issue and changes nothing (2b7c869)

## 0.43.1 — 2026-11-10

### louie

#### Fixes

- verify: find the Guidelines in a Workflow, and name each finding's source (5ca4c56)

## 0.43.0 — 2026-11-10

### louie

#### Features

- louie: run /louie:verify as a Workflow, one verifier per source (d621ab7)

## 0.42.1 — 2026-11-10

### bagheera

#### Fixes

- on a python3 older than 3.9, say louie gives no Guideline, and exit 2 (8a5bd82)

### louie

#### Fixes

- on a python3 older than 3.9, say louie gives no Guideline, and exit 2 (8a5bd82)

## 0.42.0 — 2026-11-10

### baloo

#### Breaking changes

- split louie out of baloo: the Guidelines and the verifier, for building (dddecdb)

### bagheera

#### Fixes

- doctor: name bagheera, not baloo, in the doctor skill (f2b953e)

### louie

#### Breaking changes

- split louie out of baloo: the Guidelines and the verifier, for building (dddecdb)

## 0.41.0 — 2026-11-10

### baloo

#### Breaking changes

- split bagheera out of baloo: each person's session machinery, installed once (3532a7e)

### bagheera

#### Breaking changes

- split bagheera out of baloo: each person's session machinery, installed once (3532a7e)

## 0.40.0 — 2026-11-10

### Features

- session-review: propose only what a session settled, not what it left open (6cccb4b)

## 0.39.0 — 2026-11-10

### Breaking changes

- drop the Config: the Session review always runs, and Format on edit goes (3130ce5)

## 0.38.0 — 2026-11-10

### Breaking changes

- leave the Output style and Status line to each person's own settings (3b44007)

## 0.37.0 — 2026-11-09

### Breaking changes

- keep the Checks and Guidelines always on, whatever the Config says (539ab5e)

## 0.36.0 — 2026-11-09

### Breaking changes

- leave commits to hathi: write no Git hooks, and let old ones through (97cb23c)

## 0.35.0 — 2026-11-09

### Features

- prd: have a fresh subagent read a PRD before it is agreed, and name its Anti-goals (39a4a99)
- interview: ask the approach first, and show options that look different in a preview (8c0b89b)
- verify: offer a Verification at the end of a task that serves an Issue or PRD (76a9cc1)
- principles: end a task that serves an Issue or PRD with an offer of /baloo:verify (f5cb9c9)

### Fixes

- prd: load the skill when the user agrees a PRD, so its fresh read runs (c316d42)
- prd: keep the due date out of a PRD's Success signal (c82dbe1)

## 0.34.0 — 2026-10-31

### Features

- status-line: show the project's folder before the branch (2f4ae6a)

## 0.33.0 — 2026-10-31

### Features

- inbox: go through the Session review's Inbox proposals in /baloo:inbox, not at session start (9af8b1f)

## 0.32.1 — 2026-10-31

### Fixes

- checks: let no-secrets-in-context pass counts, captured values, flags and public keys (11008fd)

## 0.32.0 — 2026-10-31

### Features

- tell Claude at session start the commit message conventional-commits takes (61ac850)

## 0.31.1 — 2026-10-31

### Fixes

- checks: don't take a jq program for a private key file when --arg comes before it (f44f3a0)

## 0.31.0 — 2026-10-30

### Features

- name a Guideline the repo fits but the Config turns off, at session start and in doctor (bc371dc)

### Fixes

- session-review: leave a blank line before each fence of a Proposal, as Markdown linters want (0ffafc8)
- retro: recommend at most three fixes worth their cost, in the project, not the user's setup (481b071)

## 0.30.0 — 2026-10-30

### Features

- guidelines: have a Go handler parse its input once into types the code behind trusts (cabb59c)
- keep ADRs and the glossary only in .about/, offering to move numbered ADRs and CONTEXT.md (28f449e)

### Fixes

- git-hooks: stay quiet at session start when core.hooksPath is /dev/null, as in an eval run (01ebb27)
- guidelines: give the ci Guideline only when a look at CI shows a failure, not at green checks (b812ab8)
- tell Claude at the first prompt after an update, not drop it as two JSON answers (f74a8d5)
- glossary: load the skill when the user asks to record or define a term (3381902)
- guidelines: give debugging for a failed test run, but not one meant to fail (c1a89d7)

## 0.29.1 — 2026-10-20

### Fixes

- adr: write into a project's own ADRs, and say why when a decision gets none (9bd57dd)
- give the testing Guideline when a test is edited, not when it is read (2870af2)

## 0.29.0 — 2026-10-19

### Features

- say when a Session review failed, cap it at $3, and review a resumed session only anew (e24838a)

## 0.28.0 — 2026-10-14

### Features

- session start names the files in .about/ that git hasn't committed (0f03c3d)
- doctor and the next prompt say when a newer version is installed than the session runs (dbbbe32)

## 0.27.0 — 2026-10-14

### Features

- give the Guidelines tied to a task when the task shows, not only by session start's index (2c52acf)

### Fixes

- guidelines: cut what principles repeats or what Claude does anyway (6000f75)

## 0.26.2 — 2026-10-14

### Fixes

- let no-secrets-in-context allow a grep of names or counts, and output into a file (ba003ef)
- leave what is still to do on a ticket out of the Session review's Inbox items (a9c5db2)

## 0.26.1 — 2026-10-14

### Fixes

- stop no-secrets-in-context denying commands that print no secret (6e0ecc7)

## 0.26.0 — 2026-10-14

### Breaking changes

- run the Hooks and Git hooks with python3 instead of a downloaded binary (65a54e9)

### Fixes

- guidelines: drop the pre-coding questions and the plan template, so Claude doesn't over-plan (a46ca63)

## 0.25.1 — 2026-10-09

### Fixes

- session-review: read a Proposal fenced with backticks, not only tildes (3b16a1d)

## 0.25.0 — 2026-10-09

### Features

- git-hooks: run the project's own command under git-hook-commands once the Checks pass (b4903ef)

## 0.24.1 — 2026-10-07

### Fixes

- session-review: start no review of an Agent SDK session either, only of one with the user (9ee77c6)

## 0.24.0 — 2026-10-07

### Features

- guidelines: give typescript, vue and testing whole when Claude first reads or edits a file (dbfdb27)

## 0.23.0 — 2026-10-07

### Features

- session-review: propose changes to .about/ for the user to accept, reject or defer (5eedae5)

## 0.22.0 — 2026-10-07

### Breaking changes

- remove the Stop check, no-destructive-commands and the checks' questions to the user (c82c986)

## 0.21.1 — 2026-10-05

### Fixes

- linear-history: pass the merges a branch brings along from the remote's default branch (f51eb51)

## 0.21.0 — 2026-10-04

### Features

- status-line: show how long the prompt cache stays warm, and the 7-day reset day (b0714f1)
- config: pick the Status line's bars, their order and thresholds (6836bf5)
- status-line: show the Cache bar last by default (ff6259a)

## 0.20.0 — 2026-10-03

### Features

- checks: refuse a commit that adds conflict markers or a file over 1 MB (afd41e9)

### Fixes

- skills: add an Inbox item without a heading for the file, as the Guidelines do (1ba3931)

## 0.19.1 — 2026-10-03

### Fixes

- loader: download the binary at the first prompt after a mid-session update (443ca78)

## 0.19.0 — 2026-10-03

### Features

- doctor: show baloo's state in a repo and what is wrong with it with /baloo:doctor (00d20fb)
- session-start: stop showing baloo's version at session start (296438b)

## 0.18.0 — 2026-10-03

### Features

- guidelines: update outdated dependencies with the dependencies Guideline (5132939)
- config: list a new Config's Guidelines and Checks sorted by name (50932e7)

## 0.17.0 — 2026-10-03

### Features

- guidelines: fix a failed CI run with the ci Guideline, on where the repo has a CI (528c61f)

### Fixes

- verify: tell a Verification apart from Claude Code's /verify, and name what to run there (9f35853)

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
