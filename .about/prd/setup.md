# bagheera sets a project up in one step, and says where a project isn't set up

## Problem

Setting a project up is a list of about a dozen items in PRD project-setup, done by hand: of the
22 git repositories in `~/Projects` on 2026-11-11, 8 are set up, 2 are half set up with the Git
hooks an earlier baloo wrote still in `.git/hooks` and no `permissions.deny` (chainofsale-v1,
vidcrunch-cto), and nothing tells the person in the other 12 that they aren't. Each item done by
hand can be done differently (`webui` runs husky without `hathi`; two repos name their ADR on it
other than `repo-setup`), and when the list grows, nothing finds the projects that lack the new
item.

## Users

- The person who works in a repo with bagheera installed and wants it set up: they ask once, read
  the diff, and commit it.
- Not for: a repo its owner decides not to set up, such as a fork whose upstream owns `CLAUDE.md`;
  it is told it isn't set up once per clone, and nothing more.

## Success signal

The 2 half set-up repos and every repo the person sets up after the Release are set up by the
skill alone: after its one run and the person's commit, `doctor` names no missing item, and no
item needed an edit by hand.

## Scope

- `/bagheera:setup` in a repo makes the working tree hold what PRD project-setup lists, and
  nothing else, leaving the commit to the person. Its mechanical part is a script of bagheera's,
  the same code `doctor` checks with; the skill asks the question, runs it, and writes the ADR.
- What it writes, beyond PRD project-setup's list:
  - `enabledPlugins` with `baloo@bunderlog` and `louie@bunderlog`, and `enableWorkflows`; not
    bagheera, which each person installs.
  - Where the project has no `.hathi.yml`, the skill asks once whether to add `hathi` (yes
    recommended). On yes, `hathi` must be on the machine, else it stops and says to install it
    with mise or brew; the pin in `mise.toml` is the installed version, 1.2.0 or later, and a
    second run leaves it. On no, it writes no Git hook, and the item stays missing for `doctor`
    unless the project already checks Secrets in a hook of its own.
  - The Git hooks: `.githooks/` with `commit-msg`, `pre-commit` and `pre-push`, each as `hathi
    hooks print <hook>` prints it; in a repo with husky (`.husky/`), the same three hooks there,
    `hathi check <hook>` first and the project's own lines after; lefthook, `pre-commit`'s
    framework, husky's older setup in `package.json`, or another manager stops it with what it
    found, since none of the machine's repos uses one and its YAML needs more than the standard
    library to edit.
  - The command that turns the hooks on, in the README's `## Development` section, the section
    added where there is none; in `CLAUDE.md` where the repo has no README.
  - The ADR `.about/adr/repo-setup.md`, in ADR adr-format's form: whether the project runs
    `hathi`, what checks Secrets, and what an earlier baloo left that the run removed.
- It keeps what the project already has: its other settings, the rest of `CLAUDE.md`, the README
  and `.gitignore`, its hook lines after `hathi`. It removes only what an earlier baloo wrote: its
  Git hooks in `.git/hooks`, a committed `outputStyle`, `.claude/baloo.yml`, and in the clone's
  `settings.local.json` the `statusLine` and `outputStyle` `doctor` already names as baloo's.
- It ends by giving the command that turns the Git hooks on in this clone, and running `doctor`.
- Run again in a set-up repo, it changes no file.
- `doctor` names, in a repo, each item of the list the checked-out files lack, a line each, with
  `/bagheera:setup` as the fix; a repo whose `.claude/settings.json` doesn't turn baloo on gets
  one line, that it isn't set up. A missing item is a problem, as `doctor`'s others are. It
  checks the README for the command, the ADR by its file, and `.hathi.yml` for each
  `conventional-commits` type.
- bagheera's session start says once per clone, the clone known by its root's path and the mark
  kept in bagheera's data folder for good, in a repo that lacks any item, that the repo isn't set
  up and `/bagheera:setup` does it; nothing in a headless session.

## Non-goals

- Installing `hathi` or mise, and turning a clone's Git hooks on: the person does (PRD
  project-setup).
- Setting up a repo that isn't the session's own, or several at once.
- Choosing a Secrets tool for a project without `hathi`.
- Removing the Checks that `permissions.deny` now covers: deny rules are a second layer under
  them, and each Check stays whole (ADR checks).
- Choosing a project's other hooks, linters or tests.
- Renaming the ADR a set-up project already keeps under another name: `doctor` names it missing,
  and the person renames it.

## Anti-goals

- The skill commits, pushes, or changes git's config.
- A project's own setting, hook line or `CLAUDE.md` text is lost or reordered beyond putting
  `hathi` first.
- A set-up repo is told at each session start that it isn't set up.

## Acceptance criteria

- In a new repo with only a README, the script with `hathi` added leaves a working tree that holds
  every item of PRD project-setup's list but the ADR, and `doctor`, the ADR written, names none
  missing.
- In a repo with husky whose `pre-commit` runs `npm test`, it leaves `.husky/pre-commit` running
  `hathi check pre-commit` and then `npm test`, adds `.husky/commit-msg` and `.husky/pre-push`, and
  writes no `.githooks/`.
- In a repo whose `.claude/settings.json` has its own `permissions.allow` and `env`, both stay as
  they were.
- In a repo with Git hooks an earlier baloo wrote (`# managed by baloo`), a committed
  `outputStyle`, `.claude/baloo.yml` and baloo's `statusLine` in `settings.local.json`, it removes
  all four; a `statusLine` of the person's own there stays.
- In a repo whose `CLAUDE.md` holds other text, the text stays, and one `@.hathi.yml` line is
  added.
- Run a second time, the script leaves every file's content as the first run left it.
- It makes no commit, and `git config --local --list` is the same before and after.
- With `hathi` added and none on the `PATH`, it stops naming mise and brew, and writes nothing.
- In a repo with husky's setup in `package.json`, it stops naming that setup, and writes nothing.
- `doctor` in a set-up repo whose `.claude/settings.json` lacks `attribution` and whose
  `.gitignore` lacks `.claude/worktrees/` names those two and no other item, each with
  `/bagheera:setup`; in a repo with none of the items, one line.
- bagheera's session start in a repo that isn't set up says so in the first session of a clone,
  not in the second, and never in a set-up repo or a headless session.
