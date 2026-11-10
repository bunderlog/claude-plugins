# Three plugins in the `bunderlog` marketplace, split by who turns a part on and what it is made of

Date: 2026-11-10

This repo is the `bunderlog` marketplace, and it holds three plugins (PRD harness): `baloo`, the
project's method — the knowledge skills and one SessionStart Hook in `sh`, no Python; `louie`,
building — the Guidelines, each given by its task's signal or named where it fits, the verifier and
the Workflows `verify`, `plan` and `deliver`, and to come templates, `batch` and `upgrade-all` (PRD
louie, PRD delivery); and `bagheera`, the person's sessions and repos — Checks in Hooks beyond
Claude Code's deny rules, the Status line and `doctor`, the Session review and Retro, the
`short-replies` Output style, and setting a project up. A part goes where who turns it on and what
it is made of put it: a project turns baloo and louie on for everyone in it, and each person turns
bagheera on once, for every session, the home folder included, so setting a project up is
bagheera's, since baloo and louie are off until it is done.

No plugin has a Config of its own: Claude Code's `enabledPlugins` is the switch, and a plugin that
is on is on whole. The plugins share no code and call none of each other's; they work together
only through files whose layout a PRD sets (`.about/`, Transcripts, the Git hooks), and a helper
copied into two plugins isn't shared code. They are released together, under one version for the
marketplace (ADR releases).

Every name the code, a plugin's and the release tool's, uses for a plugin (its name, folders and
file names) is a constant in one module of that plugin, so a rename is one edit in its code, plus
the manifests and the docs; a Workflow script repeats the names it needs, as it can't import.

A plugin's code is Python, standard library only, but its Workflows are JavaScript, the language
Claude Code runs them in; `node` is needed only by this repo's tests (PRD delivery).

New work that leans on what a plugin already has is part of that plugin, not a plugin of its own:
fixing a failed CI run is louie's `ci` Guideline (ADR guidelines), which follows `debugging` and
hands a flaky failure to the `issue` skill.

The move was made a step at a time, a Release per step: bagheera shipped with 0.41.0 and louie
with 0.42.0; louie's templates and Workflows come each with a PRD of its own.

## Considered options

- One plugin, baloo, for everything (until 2026-11-09) — a Config, its own YAML parser and a switch
  for each part, about 2,500 of its 7,100 lines of Python, only to turn on and off what
  `enabledPlugins` turns on and off; and the parts a project turns on for everyone and the parts
  a person turns on for every session came in one install.
- A plugin per role on top of baloo, which would keep only the project's knowledge: `bagheera`
  for developers, `kaa` for testers, `hathi` guarding with the Checks and Git hooks, `mowgli` for
  the person's own setup, `akela` for product managers (agreed in an interview 2026-10-05, never
  built; dropped 2026-10-07) — it rested on enforcement in code being a niche of its own, which
  the measurement didn't confirm (ADR measurement). The split taken isn't by role but by who turns
  a part on, and about 4,000 lines are left beside the knowledge.
- baloo split into smaller plugins, so each audience installs only what it needs (weighed again
  2026-10-14) — no user of such a set existed, and the Config turned off each Check and Guideline;
  the Config is gone, and the split taken isn't by audience. A plugin for another audience is still
  open in the Inbox.
- Five plugins, the Status line (`chil`) and past sessions (`kaa`) each one of their own — each
  person turns them on the same way, for every session, so the split would cost two more installs
  and two more copies of the same helpers.
- Two plugins, skills and Hooks, each installed on its own — the Hooks do nothing useful without
  the skills.
- Workflows in a plugin of their own, or in baloo — building is louie's job, and in baloo they
  would need code beyond its one session-start Hook.
- The Guidelines in baloo, louie taking only the stacks' (until 2026-11-10) — giving a Guideline
  by its task's signal takes Hooks in Python, and baloo would no longer be markdown alone; the
  rules on every task reach Claude from louie's session start just the same.
- Setting a project up in baloo — baloo is off in a repo until the repo is set up.
- A second plugin for fixing a failed CI run — it would find the local command to reproduce a
  failure on its own, which louie's `ci` Guideline already does.

## Consequences

- A person installs bagheera once; baloo and louie reach a teammate from the project's committed
  settings once the folder is trusted, which a clean machine has yet to confirm.
- bagheera's Checks are off only with bagheera or its Hooks.
- The release tool has to release several plugins under one version before the first split, and
  whether a change needs a Release depends on `plugins/` as a whole (ADR releases).
- Helpers copied into bagheera and louie (reading a Hook's input, state kept for a session) could
  drift apart: a test keeps each copied module the same as its twin but for the plugin's name,
  and each plugin keeps only the helpers it calls; each plugin's tests run on their own.
- A plugin's entry script is in `scripts/`, not `bin/`: claude.ai and Cowork don't install a plugin
  with a top-level `bin/`, and nothing needs it on the Bash tool's `PATH`, since a skill can name
  its path under `${CLAUDE_PLUGIN_ROOT}/scripts/`.
- Revisit when a part is wanted on in a way its plugin isn't (a team wanting bagheera's Checks for
  everyone in a project), or when the copied helpers outgrow a few hundred lines.
