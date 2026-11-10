# louie gives Claude the rules for building, and checks a change against what was agreed

## Problem

baloo still runs Python for its Guidelines and the verifier, so the project's method can't be
markdown alone, and how to build sits beside what was decided (PRD harness, ADR plugin).

## Users

- Everyone in a project that turns louie on: the same Guidelines and Verification for all.
- Not for: a person who wants Guidelines everywhere for themselves; louie is the project's.

## Success signal

baloo ships no Python; a project with louie on gets each Guideline by its task's signal as before.

## Scope

- louie, a plugin of the `bunderlog` marketplace released with the others under one version,
  takes from baloo: the Guidelines with the Hooks that give them by a task's signal and name the
  others at session start, the Read Hook that allows reading them, `verify` and the verifier with
  its SubagentStart Hook.
- It shares no code with baloo or bagheera; the helpers it needs are copied.
- baloo keeps its skills and one SessionStart Hook in `sh`: how many items the Inbox holds and the
  files in `.about/` git hasn't committed. A Git hook an earlier baloo wrote still lets each commit
  through, saying the plugin's code is missing.
- A Release says once that a project turns louie on beside baloo (`enabledPlugins`).

## Non-goals

- Workflows from an Issue to a pull request, `verify` as one, and templates: PRDs of their own.
- New signals for `go` or `tailwind`.

## Anti-goals

- A Guideline that reached Claude by its signal stops reaching it in a project that turns louie on.

## Acceptance criteria

- With louie on, editing a test gives Claude the `testing` Guideline once in the session, and a
  failed `mise run check` gives `debugging`.
- `plugins/baloo/` holds no Python, and its session start counts the Inbox's items and names the
  uncommitted files in `.about/`.
- `/louie:verify` runs the verifier, which is given the Guidelines that fit the repo.
- The tests of each plugin's code import only its own plugin's package.
