# louie starts a new Go and Vue product from a template, set up from its first commit

## Problem

Each new product of the operator's usual stack, Go and Vue deployed with Kamal, starts by hand:
`checkmeup` and `chainofsale` each spent their first days on the repo's layout, `mise.toml`, the
Git hooks, CI and Kamal's config, and came out different (bun with turbo against pnpm; Go 1.25
against 1.26), so a fix found in one doesn't reach the other. A project set up by hand also
commits unchecked until someone sets it up (PRD project-setup).

## Users

- The operator, or anyone in a project with louie on, starting a new product on Go, Vue and Kamal.
- Not for: a static site, a library, or another stack; an existing project, which is set up instead
  (PRD project-setup).

## Success signal

The next new product of this stack starts from `/louie:new`, and its first commit passes its own
Git hooks and CI with no file of the template changed by hand.

## Scope

- `/louie:new <path>`, a skill of louie, run from a session in any project with louie on, so louie
  needs no install of its own for it: asks the product's name (lowercase letters, digits and
  hyphens, starting with a letter, so it serves as a Go, npm and Kamal name) and the GitHub owner
  (the `gh` user by default), and has louie's code copy the `go-vue` template into `<path>`, a new
  or empty folder outside any git repo, filling in the name, the owner and today's date, and run
  `git init` on `main`. It then gives the person one line to run, `! cd <path> && mise trust &&
  mise run setup && git add -A && git commit -m "chore: scaffold from louie go-vue <version>"`:
  the person turns the Git hooks on (PRD project-setup), and the first commit, which records where
  the project came from, passes them with no trailer of Claude's. Creating the GitHub repo,
  pushing and deploying are the person's; the skill says the commands.
- The template is cut from the settled choices of `chainofsale` (its ADR stack) and of
  `checkmeup` (its CI); where they and louie's `go`, `vue`, `typescript` or `tailwind` Guidelines
  differ, the Guidelines win (eslint with their rules). It holds:
  - `apps/api`, the Go module `github.com/<owner>/<name>`, serving `GET /api/up`, with Postgres
    through sqlc and goose;
  - `apps/app`, a Vue 3 app in TypeScript with Tailwind, Vitest and eslint, named for the address it
    serves as in ADR stack;
  - a pnpm workspace, its `pnpm-lock.yaml` and `go.sum` committed with no product name in them;
  - `mise.toml` pinning every tool to an exact version (Go, Node, pnpm, `hathi`, golangci-lint,
    sqlc, goose) and naming the tasks `setup` (installs and turns the Git hooks on), `check`
    (each app's lint, types and tests, with no database), `dev` (Postgres in Docker, the API and
    Vite) and `deploy` (Kamal from its pinned Docker image);
  - a Dockerfile and Kamal's `config/deploy.yml`, the server and registry marked for the person to
    fill in, as the README says;
  - a CI that runs `hathi` and `mise run check`;
  - what PRD project-setup lists for a new project with `hathi`, `enableWorkflows` included, and an
    `.about/` with an ADR stack saying why each choice was made;
  - a local database reached with no password, so nothing in it reads as a Secret.
- `/louie:new` and the project need only git, mise and Docker; mise installs the rest.
- The template's files don't change what this repo's own sessions see: no stack Guideline, no
  `CLAUDE.md` and no settings come from them.

## Non-goals

- `upgrade-all`, bringing projects made from the template to its newer version: a PRD of its own,
  once two projects come from it.
- Templates for other stacks, a static site among them.
- Moving `checkmeup` or `chainofsale` onto the template.
- The deploy itself: the server, its secrets and the domain are the person's.

## Anti-goals

- `/louie:new` writing into a folder that isn't empty, or inside a git repo.
- A fresh project whose `mise run check` fails, or whose first commit its Git hooks refuse.
- The template breaking a rule of louie's own Guidelines.

## Acceptance criteria

- louie's code, given a new folder, a name and an owner, writes the template there with `git init`
  on `main`; in it `mise trust && mise run setup` turns the Git hooks on, the first commit with the
  skill's message passes them, `mise run check` passes, and `mise run dev` answers `GET
  /api/up` with 200 and serves the app's page, and its Dockerfile builds. Checked by a CI job of
  this repo.
- In that fresh repo, no file holds the template's name, owner or date marks, and the Go module's
  path and the app's name are the ones given; only `config/deploy.yml`'s server and registry are
  left marked for the person.
- The fresh repo's `.claude/settings.json`, `.githooks/`, `.hathi.yml`, `.gitignore` and
  `CLAUDE.md` hold what PRD project-setup lists for a new project with `hathi`.
- Every tool in the template's `mise.toml` is pinned to an exact version.
- Given a folder that holds a file, or one inside a git repo, louie's code stops, says why, and
  writes nothing.
- In this repo, session start names no stack Guideline that the template's files alone would call
  for.
- `/louie:verify` run on the fresh repo against louie's Guidelines finds no departure that blocks.
  Checked by hand at the template's Release.
