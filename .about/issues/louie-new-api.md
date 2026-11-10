# The `go-vue` template gets `apps/api`, a Go module serving `GET /api/up`

2026-11-10

## Symptom

The second of PRD templates' four Issues: `/louie:new` writes a project with no app yet (0.46.0).
This one adds `apps/api`, the Go module with Postgres through sqlc and goose, and its part of
`mise run check`. Then come `apps/app`, the Vue app, with the pnpm workspace; then `mise run
dev`, the Dockerfile, Kamal's `config/deploy.yml` and the CI job running `mise run dev`.

## Evidence

- PRD templates, Scope: `apps/api`, the Go module `github.com/<owner>/<name>`, serving `GET
  /api/up`, with Postgres through sqlc and goose; `go.sum` committed with no product name in it;
  Go, golangci-lint, sqlc and goose pinned in `mise.toml`.
- `~/Projects/chainofsale/apps/api`: `cmd/server`, `internal/…`, `migrations/` with
  `migrations.go`, `queries/`, `sqlc.yaml` generating `internal/db` on `pgx/v5`; ADR stack there.
- `~/Projects/checkmeup/mise.toml`: golangci-lint and goose pinned beside Go.
- `plugins/louie/guidelines/go.md`: the layout, errors and logs the module must follow.

## Acceptance criteria

- A repo fresh from `/louie:new` has `apps/api`, a Go module whose path is
  `github.com/<owner>/<name>` with the owner and name given, and `go.sum` committed; no file holds
  the template's marks.
- In it, `mise run check` builds and vets the module, runs golangci-lint and its tests, and fails
  when `internal/db` differs from what sqlc generates from `queries/` and `migrations/`; it needs no
  database. A test of the server's handler gets 200 from `GET /api/up`.
- The module has one goose migration and one sqlc query, with sqlc's generated code committed, so
  a product adds its own the same way.
- Go, golangci-lint, sqlc and goose are pinned to exact versions in the template's `mise.toml`.
- An owner that can't stand in a Go module path, such as one with a space or a slash, is refused
  like a bad name: louie's code stops, says why, and writes nothing.
- The template's `apps/api` follows louie's `go` Guideline, and the template's ADR stack says why
  Go, sqlc and goose.
- In this repo, session start still names no stack Guideline that the template's files alone
  would call for; this repo's CI job that makes a repo from the template still commits it through
  its hooks and passes its `mise run check`.

## Comments

### 2026-11-10 · decision

`GET /api/up` says the server is up and touches no database, so it answers 200 with Postgres down
and serves as Kamal's health check later; a check of the database, if a product wants one, is its
own route.

### 2026-11-10 · decision

The template's one migration creates a small example table, `notes` (id, body, created_at), and
its one query is `ListNotes`: it shows the whole pattern, a table, a query and the models sqlc
makes, without presuming a domain decision, and the template's ADR stack says to replace it with
the product's first real migration before its first deploy. A table most products keep, such as
`accounts`, would presume email sign-in; no table at all would show no schema to copy.
