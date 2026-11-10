# Guidelines are files given by their task's signal or named where they fit, not skills

Date: 2026-11-10

A Guideline is a file of working rules in `plugins/louie/guidelines/`: `principles`, `design`,
`testing`, `debugging` and `writing-for-agents` for any project, `ci` for a repo with a CI,
`dependencies` for one with a package manager's manifest, `go`, `typescript`, `vue` and `tailwind`
for their stacks. Each is on wherever louie is, with no switch of its own (PRD no-config). At
session start the plugin prints, for each Guideline that fits the repo, one line: when to read it
and its path.
Claude reads the file itself when a task calls for it. `principles` also carries the few rules
that must hold on every task, and those are printed whole, with the rules zsh needs where the Bash
tool's shell, `CLAUDE_CODE_SHELL` or `SHELL`, is zsh: a glob with no match or a word starting with
`=` fails the whole command there. Outside a repo session start names none. How Claude
writes its replies is not a Guideline but an Output style (ADR output-styles).

Only `go` and `tailwind` wait for Claude to read them: a Guideline was read before an edit on its
subject in 5 of 79 cases, and in one project in 0 of 29 (ADR measurement); in a week of 2026-10
it was 0 of 30 for `debugging` and the others tied to a task, while those a Hook gives came before
the first edit of their subject in 15 of 22 cases, after it in the rest. A Hook gives Claude the
whole file, as its added context, the first time in a session that a signal of its subject or
task comes:
- `PostToolUse` on Read, Edit, Write and MultiEdit, for a file in the repo: `.ts`, `.tsx`, `.mts`,
  `.cts` and `.vue` for `typescript`, `.vue` for `vue`, and a text an agent reads for
  `writing-for-agents` (`SKILL.md`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, a `.md`
  under `.claude/agents/`, `commands/` or `skills/`). Claude reads a file before it edits it, so
  the Guideline is in context before the first edit of it.
- The same, but on an edit only: a package manager's manifest for `dependencies`, which a Read
  alone doesn't give, as a `package.json` is read for its scripts too; and a test for `testing`
  (`*_test.go`, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.py`, a file under `__tests__/`), as a
  test is read to answer a question too, and `testing` given then turned the answer into code: in
  an eval of 2026-10-19, Claude Sonnet asked whether to change a design read a test, was given
  `testing`, and wrote a test-first change instead of checking the ADRs, in 6 of 8 runs; with
  `testing` given on an edit only, in 0 of 5.
- A Write that creates a code file, but a test (its result's `type` is `create`), for `design` and
  `principles`: a new module is where they apply first.
- `PostToolUse` and `PostToolUseFailure` on Bash, for the command: a run of tests or checks
  (`pytest`, `vitest`, `go test`, `npm run test:…`, `mise run check`…) that failed, by its exit or
  by what it printed, since a pipe into `tail` exits 0, for `debugging`, but a run meant to fail:
  one the same command changes files before (`git stash`, `cp`, `sed -i`, a `>` into a file), as
  breaking code to see a test go red does, and one after the session's last edit of code was to a
  test, the red step of test-first; a look at a CI run (`gh
  run`, `gh pr checks`, `glab ci`, a pipeline's API) whose output shows a failure (a failed run,
  check or step, an `##[error]` line) for `ci`, by the output alone, as `gh pr checks` exits
  non-zero on a pending check too; a change to the dependencies (`npm install <package>`, `npm
  update`, `go get`, `cargo update`…) for `dependencies`.

Each one given logs a line in the plugin's data folder, `guidelines/guidelines.log`, its fields
split by tabs: when, in UTC, the session, the Guideline, and the file, from the repo's root, or `$ `
and the command; so a measurement tells whether it came before an edit without guessing. Session
start's index leaves out every Guideline a Hook gives but `principles` and `design`: a refactor of
files already there creates none, so their line stays for Claude to read.

A headless session, `claude -p`'s or the Agent SDK's, a Session review's own too, gets the
Guidelines as any other does: session start's index and the Hooks that give them. Session start's
part is at most about 2,000 characters, under 1% of a Session review's cost, and a Hook gives a
whole Guideline only once its subject or task comes up, which is where a headless agent edits code
with nobody to correct it.

What the next measurement checks of the three is a rule each whose breach shows, with no judgment,
in the text an Edit or a Write adds (for an Edit, the lines of `new_string` not in `old_string`):
- `typescript`, no `any`: `: any`, `as any`, `<any>` or `any[]` on a line that isn't a comment;
- `vue`, no Options API: `export default {` or `defineComponent(`, or a `.vue` written whole with
  no `<script setup>`, since a second plain `<script>` beside one is allowed;
- `testing`, no fake of a module of the project: `vi.mock(` or `jest.mock(` of a path starting with
  `.`, `@/` or `~/`, counted in JavaScript and TypeScript tests only.

Before 0.24, this machine's Transcripts held 24, 4 and 2 edits on these subjects, with no breach
of any of the three rules, and none of the other rules that show in a diff (an `enum`, a class, a
built-in module imported without `node:`, `defineProps` without a type, `router.push` by path, a
`<style>` block, fake timers) reached 3 breaches either. On that data none of the three Guidelines
is measured by a rule: the next measurement counts whether a Guideline was in context before an
edit of its subject. A rule's share of breaches, before 0.24 and after, is reported only once the
other machine's Transcripts, where these stacks are worked on, show 3 or more breaches of it before
0.24.

Session start's index names a Guideline only where it fits the repo: those for any project
always, `ci` only where the repo's root holds a CI's config (`.github/workflows/`, `.gitlab-ci.yml`,
`bitbucket-pipelines.yml`, `bamboo-specs/`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci/`,
`.buildkite/`), `dependencies` only where the repo holds a package manager's manifest (`go.mod`,
`package.json`, `Cargo.toml`, `pyproject.toml`), and a stack's only where the repo's files name
that stack: `go.mod` for `go`, a `package.json` depending on `typescript` for `typescript`, one
depending on `vue` for `vue`, one depending on `tailwindcss` for `tailwind`. Session start walks
the repo for them once each time, at any depth outside hidden folders, other projects' code
(`node_modules`, `vendor`), test fixtures (`testdata`) and build output (`build`, `dist`, `out`,
`target`), so a stack the repo takes up is named from the next session on. A Hook gives a
Guideline by its signal whatever the repo's manifests: a `.ts` file read is the signal.

The files are in the plugin's folder, outside the project, where the Read tool asks the user
first, and a plugin can't ship permission rules. So the plugin adds a Hook of its own, at
`PreToolUse` for the Read tool, that allows reading a file in the plugin's `guidelines/`, and
Claude reads one without a prompt. The user's own deny and ask rules still win over it. The Hook
never stops a Read: where `python3` is missing or the plugin fails, it says nothing.

A plugin's skill can't be hidden from one project: Claude Code's `skillOverrides` doesn't apply to
a plugin's skills, and a SessionStart Hook runs after the skill listing is built. So a Guideline
as a skill would put every stack's description into every session, whatever the project.

So the plugin's skills are the ones that keep a document with the user (`adr`, `glossary`, `issue`,
`prd`), are a conversation with them (`architecture`, `inbox`, `interview`, `retro`, `tidy`), or
run as a Workflow (`verify`, ADR verify); rules for how to do a kind of task are a
Guideline, `debugging`, `ci` and `dependencies` among them: they keep no document, and one with no
CI never gets `ci`'s line.

## Considered options

- Each Guideline turned on by its own key under `guidelines` in the Config (until 2026-11-09) — a
  repo's stack taken up after its Config was made stayed off unnoticed (one project's `go`, `vue`,
  `typescript` and `tailwind` in 2026-10), and nobody recorded why a Guideline was off; turning
  baloo off is the switch (PRD no-config).
- `debugging` on any failed run of tests (until 2026-10-30) — from 2026-10-14 to 2026-10-30 it
  came 8 times where the command is known, 7 of them for a run meant to fail: 5 broke the code in
  the same command (`git stash`, `cp` and `sed -i`, `git show … >`, `cat >` a new test), and 2
  ran a test just written; about 670 words each. The rule above leaves out all 7 and keeps the 8th.
- `debugging` only for a run that fails after it passed earlier in the session — a run that breaks
  code to see a test fail passed before it too.
- `ci` on any look at a CI run (until 2026-10-24) — in a week of 2026-10 across two projects it
  came 8 times, never for a failed run: each was a look at green checks before a merge or after a
  Release, about 5,000 characters each.
- `testing` on a Read of a test too (until 2026-10-19) — in context before the first edit of a
  test, but a test read to answer a question about a design gave it, and Claude Sonnet then
  coded instead of answering (see above).
- Only the index line for `typescript`, `vue` and `testing` too (until 2026-10-07) — Claude read
  a Guideline before an edit on its subject in 5 of 79 cases (ADR measurement).
- Only the index line for the Guidelines tied to a task (until 2026-10-14) — Claude read
  `principles` before the first edit in 2 of 30 sessions, `design` in 1, `debugging` and the
  others in none.
- `principles` and `design` at the first edit of code in a session — they would come with nearly
  every session, about 8,000 characters, a trivial edit's too.
- A prompt's words as the signal for `ci` or `debugging` ("CI is red", "fix the bug") — a
  language's words each, and the commands Claude runs first say it anyway.
- The project's own rules, `.claude/rules/*.md` with `paths:`, which Claude Code loads when Claude
  reads or edits a matching file — a plugin can't ship rules, so the plugin would write files into
  every repo, and a rule linked from outside the repo loads only without `paths:`.
- The user's rules, `~/.claude/rules/*.md` with `paths:` — the plugin would write into Claude
  Code's own folder, which it never does (ADR config), a rule there applies to every project
  whatever its Config says, and Claude Code's docs don't say `paths:` works there. Revisit when
  Claude Code lets a plugin ship rules, or documents `paths:` in the user's rules: Claude Code's
  own loading would then replace the Hook, and its `InstructionsLoaded` Hook can record each load.
- The Guideline given at `PreToolUse`, before the call — Claude Code adds a Hook's context next to
  the tool's result, so it comes no sooner than after the Read before the edit.
- A skill per Guideline, with no key (until 2026-09-30) — no Hook for them, no stack detection,
  no permission to read from the plugin's folder, but every session gets every stack's
  description, and a project can't turn one off.
- `debugging` as a skill — `/debugging` calls it by name, but its description is in every
  session and no project can turn it off.
- `ci` as a skill (until 2026-10-03) — `/baloo:ci` calls it by name, and it commits and asks the
  user before a push, but its description was in every session, a project with no CI too, and
  it leans on `debugging`, which a project may have turned off.
- No Guidelines in a headless session, as no Proposals are shown there, or only session start's
  index there — it saves about 2,000 characters a session, and leaves an agent that edits code
  unattended without the rules it needs most.
- Printing each Guideline turned on whole — simpler, but every session pays for the rules of
  tasks it never gets to.
- The rules for every task printed always, with no key — the one part of the plugin in the
  context that the Config can't turn off.
- Every Guideline on in a new Config, as the Checks are — every stack in every repo, the context
  cost this is meant to avoid.
- A rule allowing `Read` of the folder in `.claude/settings.local.json` — the plugin's folder
  changes with every version, and that file is Claude Code's to write, not the plugin's.
- Leaving the prompt — the user is asked on every session's first Guideline, for the plugin's
  own read-only text.
- Turning a fitting Guideline's key on at session start — the Config is the user's, and a key
  written `false` at creation can't be told from one turned off on purpose.
- Detecting the stacks at every session start, with no keys — a project can't turn off a
  Guideline for a stack it has, and a repo about to start one can't turn it on.

## Consequences

- Outside a repo, and in Claude Code's own folder, no Guideline is named.
- A repo that takes up a stack, a CI or a package manager has its Guideline named from the next
  session start.
- Session start walks the repo for the stacks: a few milliseconds in a repo of these sizes, more
  in a large one.
- Every Guideline needs its file and the index line it prints; adding one is a file and a line.
- The Hook runs on every Read, whatever the file, since a Hook picks its calls by tool name; the
  Hook's `sh` starts Python only for a path with `/guidelines/` in it (ADR binary).
- Reading a Guideline asks the user where `python3` isn't there to allow it, and where their
  own ask rule covers the file.
- The allow covers every file in `guidelines/`, one that doesn't fit the repo too: it is the
  plugin's own text, and reading one is Claude's step, not the context's cost.
- `typescript` and `vue` come only after a Write that creates a file: a new component is written
  without them. `testing` comes after the first edit or Write of a test in a session, so that
  edit is made without it.
- A file Claude reads with `cat` in Bash gives nothing: its Guideline comes with the first edit of
  it, after that edit.
- Those late first edits cost little so far: from 2026-10-08 to 2026-10-31, the first edits of a
  file made before its Guideline came broke a rule a pattern can find (`any`, `enum`, a class, a
  Node built-in without `node:`, the Options API, untyped props) in 1 of 8, those made after it in
  1 of 81, and a test was run before the next edit of code in 13 of 13 and 14 of 14. Revisit if a
  session shows a late edit breaking its Guideline.
- `debugging` still comes where a test fails on purpose in a way the command doesn't show, such
  as a fix taken out by a Python script, or a red step after an edit of code that isn't a test. `ci` also comes where the output names a failure the task isn't
  about, a run list's old failed run or a PR titled with "fail"; `ci`
  and `dependencies` come after the command that signals them, before what follows it.
- A refactor of files already there gets `principles` and `design` only where Claude reads them.
- Every Bash command runs the Hook's Python once more after it.
- Every Read runs the Hook's `sh` once more, and a Guideline a Hook gives adds 2,000 to 6,000
  characters to a session once its subject or task comes up.
- Whether `go` and `tailwind` are read is Claude's call; a rule that must always hold goes among
  the ones `principles` prints whole.
- Revisit when Claude Code lets a project hide a plugin's skills, when a measurement finds a
  Guideline given where its task never came, or when Claude Code lets a plugin ship rules.
