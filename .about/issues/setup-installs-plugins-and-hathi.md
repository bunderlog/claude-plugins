# `/bagheera:setup` installs the plugins and `hathi`, and turns the Git hooks on

2026-11-16

## Symptom

PRD setup now says `/bagheera:setup` does every part of setting a project up that it can do
itself, and `doctor` names what is still wrong with `/bagheera:setup` as the fix (commit
ec7711b). The code still leaves three parts to the person:

- A plugin the project turns on but Claude Code has no install of, or an install older than the
  Release: `doctor` tells the person to run `/plugin` or `claude plugin update` by hand.
- `hathi` missing or older than 1.2.0: setup stops with "install it with mise or brew".
- The clone's Git hooks off: setup prints the command under `left:` for the person to run.

The machine's other projects show the same: `doctor` lists four projects with baloo 0.29.1 to
0.62.0 installed while 0.63.1 is released, each with `claude plugin update baloo@bunderlog there`,
and `/bagheera:setup --others` doesn't offer them, since none lacks an item.

## Evidence

- `plugins/bagheera/scripts/bagheera/doctor.py:91-102`: the two plugin problems name `/plugin`
  and `claude plugin update` as the fix.
- `plugins/bagheera/scripts/bagheera/attention.py:298-303`: an old install's fix is `claude plugin
  update <name> there`, a clone with its Git hooks off is told the command; a plugin turned on
  with no install isn't a Need at all.
- `plugins/bagheera/scripts/bagheera/attention.py:314-321`: `lacking` offers only projects with a
  Need whose fix is `/bagheera:setup there`.
- `plugins/bagheera/scripts/bagheera/setup.py:309-310`: the Git hooks command goes to `left:`;
  `setup.py:511-519` stops where `hathi` is missing or old.
- `plugins/bagheera/skills/setup/SKILL.md:10,20-21,55`: "change no git config", "installing
  `hathi` with mise or brew", "`! <command>` runs it here".
- ADR doctor names `/plugin` and `claude plugin update` among the fixes; ADR git-hooks says only
  the setup skill writes Git hooks, and nothing of turning them on.

## Acceptance criteria

- Each criterion PRD setup gives on installing and updating a plugin, installing `hathi` with
  mise, turning the Git hooks on, and `git config --local --list` changing only in
  `core.hooksPath` passes, with the test it names under `tests/bagheera/`.
- `doctor` in a repo that turns `louie@bunderlog` on with no install of it, or with an install
  older than the bagheera installed, names it with `/bagheera:setup` as the fix, and names neither
  `/plugin` nor `claude plugin update` (PRD setup's criterion on `Doctor.test_project_plugins`).
- `attention.needs` gives a project whose plugin is not installed or older than the Release, or
  whose clone has its Git hooks off, a Need whose fix is `/bagheera:setup there`, and
  `setup --others` lists such a project even where it lacks no item (PRD visibility's
  `Needs.test_old_install`, `Needs.test_hooks_off`, and PRD setup's `Setup.test_others`).
- The setup skill's `SKILL.md` no longer says it changes no git config or names brew, and its
  report names what was installed or updated as loading from the next session.
- ADR doctor no longer names `/plugin` or `claude plugin update` as a fix, and ADR git-hooks says
  the setup skill turns the clone's Git hooks on.
- `mise run check` passes.

## Comments

### 2026-11-16 · Open decision: what exit 1 means

The setup skill reads exit 1 as "it wrote nothing" (`SKILL.md` step 3), while PRD setup's
criterion has the run exit 1 where `claude` is missing or fails, after writing every other item.
Either the skill learns a second meaning of exit 1, or a failed install, update or hooks command
goes into `left:` with exit 0 and the PRD's criterion changes to match.

### 2026-11-16 · fix option: where each step runs

`setup.run` raises Stop before writing anything; installing `hathi` belongs before that point,
since the pin and the Git hooks need it, and a mise failure is a Stop. Installing and updating
the plugins and turning the Git hooks on come after the writes and never stop the run: each
failure is a line with its command and error. `hathi` installed by mise may not be on the
script's `PATH` until mise's shims are: check with `shutil.which` after the install, and Stop
naming mise's activation where it still isn't.

### 2026-11-16 · test note

`Setup.test_second_run` asserts git's config is unchanged; it changes to allow `core.hooksPath`.
Tests that set the repo up run with a `PATH` of the stand-in `hathi` and `/usr/bin:/bin`: the
stand-in `claude`, `mise` and `npm` go in the same folder, so no test reaches a real one.
