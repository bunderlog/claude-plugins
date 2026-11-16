# bagheera sets a project up in one step, the machine's other projects too, and says where a
project isn't set up


## Problem

Setting a project up is a list of about a dozen items in PRD project-setup, done by hand: of the
22 git repositories in `~/Projects` on 2026-11-11, 8 are set up, 2 are half set up with the Git
hooks an earlier baloo wrote still in `.git/hooks` and no `permissions.deny` (chainofsale-v1,
vidcrunch-cto), and nothing tells the person in the other 12 that they aren't. Each item done by
hand can be done differently (`webui` runs husky without `hathi`; two repos name their ADR on it
other than `repo-setup`), and when the list grows, nothing finds the projects that lack the new
item.

Two things an item's presence doesn't cover. A project turns a plugin on in its committed
`.claude/settings.json`, but nothing says whether that plugin is installed, or which version: on
2026-11-13, 4 projects (checkmeup, chainofsale, sagsuget.co.il, mongo-leader) turn
`louie@bunderlog` on with no install of it for them, so louie's Guidelines and agents load in
none of them, and 6 projects have baloo 0.20.0 to 0.34.0 installed with 0.61.1 released, while
`doctor` says `No problems`. And a missing item is fixed only from a session in that project: on
the same day `doctor` named 5 projects lacking an item, each needing a session of its own.

## Users

- The person who works in a repo with bagheera installed and wants it set up: they ask once, read
  the diff, and commit it.
- The same person for the machine's other projects: `doctor` names those lacking an item (PRD
  visibility), and they complete them from the session they are already in.
- Not for: a repo its owner decides not to set up, such as a fork whose upstream owns `CLAUDE.md`;
  it is told it isn't set up once per clone, and nothing more.

## Success signal

The 2 half set-up repos and every repo the person sets up after the Release are set up by the
skill alone: after its one run and the person's commit, `doctor` names no missing item, and no
item needed an edit by hand. The 5 projects `doctor` named lacking an item on 2026-11-13 hold
every item after one session in one of them, with no session opened in the others; and each
project that turns a plugin on without an install of it, or with one older than the Release the
person has, has it installed or updated by that same run, with no `/plugin` typed by hand.

## Scope

- `/bagheera:setup` does every part of setting a project up that it can do itself, and `doctor`
  names what is still wrong, with `/bagheera:setup` as the fix for each part the skill does.
- `/bagheera:setup` in a repo makes the working tree hold what PRD project-setup lists, and
  nothing else, leaving the commit to the person. Its mechanical part is a script of bagheera's,
  the same code `doctor` checks with; the skill asks the question, runs it, and writes the ADR.
- What it writes, beyond PRD project-setup's list:
  - `enabledPlugins` with `baloo@bunderlog` and `louie@bunderlog`, and `enableWorkflows`; not
    bagheera, which each person installs.
  - Where the project has no `.hathi.yml`, the skill asks once whether to add `hathi` (yes
    recommended). On yes, where `hathi` isn't on the `PATH` or is older than 1.2.0, it installs
    the latest with `mise use --global "github:bunderlog/hathi@latest"`, mise being how `hathi`'s
    README installs it; with no `mise` on the `PATH`, or where that fails, it stops, says to
    install `hathi` with mise, and writes nothing. The pin in `mise.toml` is the installed
    version, 1.2.0 or later, and a second run leaves it. On no, it writes no Git hook, and the
    item stays missing for `doctor`
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
- It installs each plugin `doctor` names not installed for the repo, `claude plugin install
  <name>@bunderlog --scope project` run in the repo, and updates each it names older than the
  Release, `claude plugin update <name>@bunderlog` with the scope of the install recorded. Neither
  changes a committed file, since the project scope's `enabledPlugins` already turns the plugin
  on. Where `claude` isn't on the `PATH` or the command fails, it names the plugin with the
  command and the error, and the rest of the run is still done. What it installed or updated
  loads from the next session, which the report says.
- It turns the Git hooks on in this clone, where git doesn't run them from the committed folder
  yet (PRD project-setup), by running the command it writes into the README: `git config
  core.hooksPath .githooks`, or husky's `npm install`. Where that command fails, it names it with
  the error for the person to run, and the rest of the run is still done. It ends by running
  `doctor`.
- Run again in a set-up repo, it changes no file.
- `doctor` names, in a repo, each item of the list the checked-out files lack, a line each, with
  `/bagheera:setup` as the fix; a repo whose `.claude/settings.json` doesn't turn baloo on gets
  one line, that it isn't set up. A missing item is a problem, as `doctor`'s others are. It
  checks the README for the command, the ADR by its file, and `.hathi.yml` for each
  `conventional-commits` type.
- `doctor` also names, in the repo it runs in, each of the plugins setting a project up turns on
  (`baloo@bunderlog`, `louie@bunderlog`) whose key in the repo's `.claude/settings.json` is true
  and for which Claude Code records no install, and each whose recorded install is older than the
  bagheera installed on the machine, which is the Release the person has, since the three plugins
  carry one version at each Release (PRD bagheera), each with `/bagheera:setup` as the fix. An
  install counts for
  the repo when its `projectPath` is the repo, whatever its scope, else when its scope is `user`,
  as `doctor` already reads bagheera's own version from `plugins/installed_plugins.json`, which
  is Claude Code's and undocumented, so a shape it can't read says nothing. Each is a problem of
  the repo `doctor` runs in, and ADR doctor is amended by the change that builds this.
- `/bagheera:setup` offers the machine's other projects `doctor` names as lacking an item or with
  a plugin not installed or older than the Release, or with its Git hooks off in that clone (PRD
  visibility), whether or not its own repo lacked one or its run stopped, and does in each
  project the person picks what it does in its own: the same script, installing and updating the
  plugins, the `hathi` question where the project has no `.hathi.yml`, asked for every picked
  project in one round, the ADR, and turning that clone's Git hooks on. It offers only a project
  that is set up: one that
  isn't is told once per clone and nothing more, since its owner may have chosen not to. A picked
  project whose run stops is named with what stopped it, and the others are still done. Each
  project's commit stays the person's, and the skill ends by saying which files it wrote in which
  project.
- bagheera's session start says once per clone, the clone known by its root's path and the mark
  kept in bagheera's data folder for good, in a repo that lacks any item, that the repo isn't set
  up and `/bagheera:setup` does it; nothing in a headless session.

## Non-goals

- Installing mise: the person does.
- Setting up, from another project's session, a repo that isn't set up at all: the person runs
  the skill in it, where the `hathi` question is theirs to answer.
- Installing bagheera itself, or a plugin the repo's `.claude/settings.json` doesn't turn on.
- Restarting the session so a plugin installed or updated loads in it.
- Telling a project that a newer version exists on GitHub: the versions compared are local (ADR
  doctor).
- Choosing a Secrets tool for a project without `hathi`.
- Removing the Checks that `permissions.deny` now covers: deny rules are a second layer under
  them, and each Check stays whole (ADR checks).
- Choosing a project's other hooks, linters or tests.
- Renaming the ADR a set-up project already keeps under another name: `doctor` names it missing,
  and the person renames it.

## Anti-goals

- The skill commits, pushes, or changes git's config beyond `core.hooksPath`, set only to turn
  the project's committed Git hooks on.
- A project's own setting, hook line or `CLAUDE.md` text is lost or reordered beyond putting
  `hathi` first.
- A set-up repo is told at each session start that it isn't set up.
- A run in another project leaves a change the person is never told about, or sets up a project
  whose owner chose not to.

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
- It makes no commit, and `git config --local --list` differs before and after only in
  `core.hooksPath`, set to `.githooks` where it was unset, and left where it already was.
- In a repo with husky, it runs `npm install` there, checked with a stand-in `npm` on the `PATH`;
  with one that exits non-zero, it names `npm install` with the error, and still writes every
  item.
- With `hathi` added and none on the `PATH`, it runs `mise use --global
  "github:bunderlog/hathi@latest"`, checked with a stand-in `mise` that puts a `hathi` on the
  `PATH`, and pins that `hathi`'s version in `mise.toml`; with neither on the `PATH`, it stops
  naming mise, and writes nothing.
- In a repo with husky's setup in `package.json`, it stops naming that setup, and writes nothing.
- `doctor` in a set-up repo whose `.claude/settings.json` lacks `attribution` and whose
  `.gitignore` lacks `.claude/worktrees/` names those two and no other item, each with
  `/bagheera:setup`; in a repo with none of the items, one line.
- bagheera's session start in a repo that isn't set up says so in the first session of a clone,
  not in the second, and never in a set-up repo or a headless session.
- In a repo whose `.claude/settings.json` turns `louie@bunderlog` on and for which Claude Code
  records no install of it, `doctor` names it a problem, with `/bagheera:setup`; with an install
  of 0.34.0 recorded while the bagheera installed is 0.61.1, it names it older, with
  `/bagheera:setup`; with an install of that same version, or with the key set to
  `false`, it names neither. An install recorded for the repo under any scope counts, a `user`
  one where the repo has none.
  → test: tests/bagheera/test_doctor.py "Doctor.test_project_plugins"
- With `installed_plugins.json` gone, or holding a shape the code can't read, `doctor` names
  neither problem and says nothing of any plugin's installed version, bagheera's own included.
  → test: tests/bagheera/test_doctor.py "Doctor.test_no_records"
- In a repo that turns `louie@bunderlog` on with no install of it, and `baloo@bunderlog` on with
  an install of 0.34.0 at project scope while the bagheera installed is 0.61.1, the script runs
  `claude plugin install louie@bunderlog --scope project` and `claude plugin update
  baloo@bunderlog --scope project` in the repo, checked with a stand-in `claude` on the `PATH`
  that records its arguments and folder, and changes no committed file.
- With no `claude` on the `PATH`, or one that exits non-zero, the script names each plugin with
  its command and the error, still writes every other item, and exits 1.
- The list the script gives the skill holds each of the machine's projects that is set up and
  lacks an item, has a plugin not installed or older than the Release, or has its Git hooks off,
  and neither one that isn't set up nor the repo the session is in.
  → test: tests/bagheera/test_attention.py "Lacking.test_lacking"
  → test: tests/bagheera/test_attention.py "Lacking.test_lacking_subfolder"
  → test: tests/bagheera/test_setup.py "Setup.test_others"
- The script, given a project that is set up and lacks an item, leaves its working tree holding
  every item of PRD project-setup's list but the ADR, and makes no commit there; given one that
  isn't set up, it names it and writes nothing.
  → test: tests/bagheera/test_setup.py "Setup.test_in_another_project"
- Given two projects of which one's `package.json` holds husky's setup, the script names that one
  with what stopped it, and leaves the other holding every item.
  → test: tests/bagheera/test_setup.py "Setup.test_in_another_project_stops"
- The script named no other project writes nothing outside the session's own repo, checked by a
  test that compares every other project's files before and after.
  → test: tests/bagheera/test_setup.py "Setup.test_leaves_other_projects"
- In a session in one project, with two others lacking an item and one of those without
  `.hathi.yml`, `/bagheera:setup` asks the `hathi` question once, for that project alone, and
  after the run and the commits `doctor` names no item missing in either. Checked by hand once.
