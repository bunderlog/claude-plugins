# Stack: one repository, mise for every tool and task, hathi in the Git hooks and CI

Date: __DATE__

__NAME__ started from louie's `go-vue` template, as its first commit names with the template's
version, and was set up for bunderlog's plugins from that commit (PRD project-setup): there was
nothing of an earlier setup to move off.

**Stability decides tool choices**: a mature tool over a faster or newer one, exact versions
pinned in `mise.toml` and lockfiles, no beta or `@latest` dependency.

The code is on GitHub, `__OWNER__/__NAME__`, and its CI is GitHub Actions'.

mise pins every tool to an exact version and is the one entry point for tasks, so `mise run
<task>` works the same on any machine and in CI: `mise run setup` installs the tools and turns the
Git hooks on, and `mise run check` is what CI runs.

The project runs `hathi`: the Git hooks are the scripts in `.githooks/`, each running `hathi check
<hook>` as `hathi hooks print <hook>` prints it, and CI runs `hathi check ci` over each push and
pull request. `hathi` is what checks commits for Secrets, and `.hathi.yml` lists the commit types
in full for `CLAUDE.md` to import, every other Check at its defaults. Each clone turns the hooks on
once with `mise run setup`, which runs `git config core.hooksPath .githooks`.

Until the apps exist, the Git hooks are the project's only code, so `mise run check` lints them
with shellcheck, pinned like every other tool.

The apps come later, each in `apps/`, named after the address it serves, and each adds its tools to
`mise.toml` and its part to `mise run check`.

## Considered options

- `hathi doctor` as the check until the apps exist — it reports Git hooks that aren't on, and in CI
  they never are, so check would fail for a reason that isn't the code's.
- A `check` task that checks nothing until the apps exist — it would pass for the wrong reason.
- Git hooks in `.git/hooks`, written per clone — untracked, so a teammate's clone has none until
  someone writes them, and two clones drift.
- Tools installed by each person, or versions left floating — a tool's new release breaks one
  machine or CI and not another.

## Consequences

- Each clone needs git and mise; mise installs the rest.
- A commit or push fails where `hathi` isn't installed, so `mise run setup` comes first.
- Raising a tool's version is an edit to `mise.toml`, and CI runs the new one with it.
