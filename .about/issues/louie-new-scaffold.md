# `/louie:new` writes the `go-vue` template's project files into a new folder

2026-11-10

## Symptom

PRD templates is agreed but nothing of it is built: louie has no skills and no template. This is
its first step: `/louie:new <path>` and louie's code that writes the `go-vue` template, holding
only the project's own files so far: what PRD project-setup lists for a new project with `hathi`,
`mise.toml`, the CI and `.about/`. The apps come in later steps, so each step is small enough to
plan and check on its own.

## Evidence

- PRD templates, Scope: the skill, the name and owner it asks, the folder it accepts, `git init`
  on `main`, the one line it gives the person to run.
- PRD project-setup, Scope: the files a set-up project commits, with `hathi`.
- `plugins/louie/` has `agents`, `guidelines`, `hooks`, `scripts` and `workflows`, no `skills`.
- The template is cut from `~/Projects/chainofsale` (its `.about/adr/stack.md`) and
  `~/Projects/checkmeup` (its `.github/workflows/ci.yml`), louie's Guidelines winning where they
  differ.

## Acceptance criteria

- louie's code, given a new folder, a name and an owner, writes the template there and runs `git
  init` on `main`; in it `mise trust && mise run setup` turns the Git hooks on, a first commit with
  the skill's message, `chore: scaffold from louie go-vue <version>`, passes them, and `mise run
  check` passes. Checked by a CI job of this repo (PRD templates, the first criterion, without
  `mise run dev`, which comes with the apps).
- In that fresh repo, no file holds the template's name, owner or date marks.
- The fresh repo's `.claude/settings.json`, `.githooks/`, `.hathi.yml`, `.gitignore` and
  `CLAUDE.md` hold what PRD project-setup lists for a new project with `hathi`, `louie@bunderlog`
  and `enableWorkflows` included, and its `.about/adr/stack.md` says why each choice so far was
  made.
- Every tool in the template's `mise.toml` is pinned to an exact version, `github:bunderlog/hathi`
  1.2.0 or later among them.
- The template's CI runs `hathi` and `mise run check`.
- Given a folder that holds a file, or one inside a git repo, or a name that isn't lowercase
  letters, digits and hyphens starting with a letter, louie's code stops, says why, and writes
  nothing.
- `/louie:new` is a skill of louie that asks the name and the owner (the `gh` user by default),
  runs louie's code, and gives the person the one line to run; with every other plugin of the
  marketplace off, it loads (PRD harness).
- In this repo, session start names no stack Guideline that the template's files alone would call
  for.

## Comments

### 2026-11-10 · order

PRD templates is built in four Issues, one after another: this one; `apps/api`, the Go module
with `GET /api/up`, Postgres through sqlc and goose; `apps/app`, the Vue app, and the pnpm
workspace; then `mise run dev`, the Dockerfile and Kamal's `config/deploy.yml`, and the CI job
running `mise run dev`. Each adds its tools to `mise.toml` and its part to `mise run check`.

### 2026-11-10 · decision

Until the apps exist, the template's `mise run check` runs `shellcheck .githooks/*`, with
shellcheck pinned in its `mise.toml`: the Git hooks are this step's only code, so it is a real
check, where a task that checks nothing would pass for the wrong reason. `hathi doctor` was the
other option, but it reports hooks that aren't on, which they aren't in CI.
