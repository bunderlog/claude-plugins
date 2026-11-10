# A template's files keep their real names, but for those that would act in this repo

Date: 2026-11-10

louie's templates live in `plugins/louie/templates/<template>/`, `go-vue` the first (PRD
templates). A template's file keeps its real name, so louie's Guidelines, gofmt and eslint reach
the template's code as they reach any other. Only a file that Claude Code, git or a tool would act
on in this repo by its real name carries the suffix `.tmpl`, which `/louie:new` drops as it writes
the file: `CLAUDE.md`, `.claude/settings.json`, `.gitignore`, `mise.toml`, `go.mod`,
`package.json` and `pnpm-workspace.yaml`.

Where the product's name, its owner or today's date goes, a file holds the mark `__NAME__`,
`__OWNER__` or `__DATE__`, which `/louie:new` fills in in every file it writes.

## Considered options

- Every file of a template with `.tmpl` — nothing of it would act in this repo, but the
  Guidelines, gofmt and eslint wouldn't reach its code either.

## Consequences

- A file added to a template gets `.tmpl` if its kind acts in this repo by its real name.
- What a template's code is checked against runs on a repo written from it, not in this repo: this
  repo's CI writes one and runs its Git hooks, `mise run check` and `mise run dev` (PRD templates).
