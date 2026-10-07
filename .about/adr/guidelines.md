# Guidelines are files the Config turns on one by one, not skills

Date: 2026-10-07

A Guideline is a file of working rules in `plugins/baloo/guidelines/`: `principles`, `design`,
`testing`, `debugging` and `writing-for-agents` for any project, `ci` for a repo with a CI,
`dependencies` for one with a package manager's manifest, `go`, `typescript`, `vue` and `tailwind`
for their stacks. Each turns on with a key of its own in the Config, under `guidelines`. At session
start the binary prints, for each Guideline turned on, one line: when to read it and its path.
Claude reads the file itself when a task calls for it. `principles` also carries the few rules
that must hold on every task, and those are printed whole, with the rules zsh needs where the Bash
tool's shell, `CLAUDE_CODE_SHELL` or `SHELL`, is zsh: a glob with no match or a word starting with
`=` fails the whole command there. A Guideline that is off puts nothing in the context. How Claude
writes its replies is not a Guideline but an Output style (ADR output-styles).

`typescript`, `vue` and `testing` don't wait for Claude to read them: a Guideline was read before an
edit on its subject in 5 of 79 cases, and in one project in 0 of 29 (ADR measurement). A
`PostToolUse` Hook on Read, Edit, Write and MultiEdit gives Claude the whole file, as the Hook's
added context, the first time in a session that it reads or edits a file in the repo of its subject:
`.ts`, `.tsx`, `.mts`, `.cts` and `.vue` for `typescript`, `.vue` for `vue`, and a test for
`testing` (`*_test.go`, `*.test.*`, `*.spec.*`, `test_*.py`, `*_test.py`, a file under
`__tests__/`). Claude reads a file before it edits it, so the Guideline is in context before the
first edit of it. The same call logs a line in the plugin's data folder,
`guidelines/guidelines.log`, its fields split by tabs: when, in UTC, the session, the Guideline and
the file, from the repo's root; so a measurement tells whether it came before an edit without
guessing. Session start's index leaves the three out. A Guideline tied to a task rather than a file,
such as `debugging`, `ci` or `design`, stays in the index, Claude's to read (Inbox).

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

A new Config turns on the Guidelines for any project, `ci` only where the repo's root holds a CI's
config (`.github/workflows/`, `.gitlab-ci.yml`, `bitbucket-pipelines.yml`, `bamboo-specs/`,
`Jenkinsfile`, `azure-pipelines.yml`, `.circleci/`, `.buildkite/`), `dependencies` only where the
repo holds a package manager's manifest (`go.mod`, `package.json`, `Cargo.toml`,
`pyproject.toml`), and a stack's only where the repo's files name that stack: `go.mod` for `go`, a
`package.json` depending on `typescript` for `typescript`, one depending on `vue` for `vue`, one
depending on `tailwindcss` for `tailwind`. Manifests and stacks are found at any depth outside
hidden folders, other projects' code (`node_modules`, `vendor`), test fixtures (`testdata`) and
build output (`build`, `dist`, `out`, `target`). They are looked for only then; from then on the
Config is the user's, like every other setting in it (ADR config).

The files are in the plugin's folder, outside the project, where the Read tool asks the user
first, and a plugin can't ship permission rules. So the plugin adds a Hook of its own, at
`PreToolUse` for the Read tool, that allows reading a file in the plugin's `guidelines/`, and
Claude reads one without a prompt. The user's own deny and ask rules still win over it. The Hook
never stops a Read: where the binary is missing or fails, it says nothing.

A plugin's skill can't be hidden from one project: Claude Code's `skillOverrides` doesn't apply to
a plugin's skills, and a SessionStart Hook runs after the skill listing is built. So a Guideline
as a skill would put every stack's description into every session, whatever the project.

So the plugin's skills are the ones that keep a document with the user (`adr`, `glossary`, `issue`,
`prd`), are a conversation with them (`architecture`, `inbox`, `interview`, `retro`, `tidy`), or
run the plugin's agent (`verify`, ADR verify); rules for how to do a kind of task are a
Guideline, `debugging`, `ci` and `dependencies` among them: they keep no document, and as
Guidelines a project can turn them off, and one with no CI never gets `ci`'s line.

## Considered options

- Only the index line for `typescript`, `vue` and `testing` too (until 2026-10-07) — Claude read
  a Guideline before an edit on its subject in 5 of 79 cases (ADR measurement).
- The project's own rules, `.claude/rules/*.md` with `paths:`, which Claude Code loads when Claude
  reads or edits a matching file — a plugin can't ship rules, so the binary would write files into
  every repo, and a rule linked from outside the repo loads only without `paths:`.
- The user's rules, `~/.claude/rules/*.md` with `paths:` — the binary would write into Claude
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
- Printing each Guideline turned on whole — simpler, but every session pays for the rules of
  tasks it never gets to.
- The rules for every task printed always, with no key — the one part of the plugin in the
  context that the Config can't turn off.
- Every Guideline on in a new Config, as the Checks are — every stack in every repo, the context
  cost this is meant to avoid.
- A rule allowing `Read` of the folder in `.claude/settings.local.json` — the plugin's folder
  changes with every version, and that file is Claude Code's to write, not the binary's.
- Leaving the prompt — the user is asked on every session's first Guideline, for the plugin's
  own read-only text.
- Detecting the stacks at every session start, with no keys — a project can't turn off a
  Guideline for a stack it has, and a repo about to start one can't turn it on.

## Consequences

- Outside a repo, and in Claude Code's own folder, there is no Config, so no Guideline is on.
- A repo that takes up a stack, a CI or a package manager after its Config was made gets its
  Guideline only when someone turns its key on.
- Every Guideline needs a key in the Config and the schema, and the index line it prints; adding
  one is a file and a key.
- The Hook runs on every Read, whatever the file, since a Hook picks its calls by tool name; the
  Loader runs the binary only for a path with `/guidelines/` in it.
- Reading a Guideline asks the user where the binary isn't there to allow it, and where their
  own ask rule covers the file.
- The allow covers every file in `guidelines/`, a Guideline that is off too: it is the plugin's
  own text, and reading one is Claude's step, not the context's cost.
- `typescript`, `vue` and `testing` come only after a Write that creates a file: a new test,
  written test-first, or a new component is written without them.
- Every Read runs the binary once more, and one of the three Guidelines adds up to about 4,000
  characters to a session once its subject comes up.
- Whether one of the other Guidelines is read is Claude's call; a rule that must always hold goes
  among the ones `principles` prints whole.
- Revisit when Claude Code lets a project hide a plugin's skills, and `debugging` as a skill when
  Claude doesn't open it on a bug by itself.
