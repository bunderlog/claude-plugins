# Stack: one repository, mise for every tool and task, hathi in the Git hooks and CI, Go with sqlc and goose

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

`mise run check` lints the Git hooks' `sh` with shellcheck, pinned like every other tool, and
then checks each app. The apps are each in `apps/`, named after the address it serves, and each
adds its tools to `mise.toml` and its part to `mise run check`.

`apps/api` is the API, a Go module whose path is `github.com/__OWNER__/__NAME__`. Go because it
deploys as one binary, serves many requests at once with no framework, and is the stack its
operator already runs. Go is pinned to 1.26.10, a mature line over a newer one, and `go.mod`'s
`go` directive names the same version. The module follows louie's `go` Guideline:
`cmd/server/main.go` wires the server up and nothing else, each package of `internal/` is named
for what it provides, `internal/respond` alone writes responses, and the tests use the standard
`testing` package. Its one route, `GET /api/up`, says the server is up and touches no database, so
it answers 200 whatever Postgres is doing; the standard library's `http.ServeMux` routes it.
golangci-lint runs at its v2 defaults, with no config.

Postgres is reached through sqlc on `pgx/v5`: queries are written as SQL in `apps/api/queries/`
and sqlc generates the Go that runs them into `apps/api/internal/db/`, which is committed and
never edited by hand. `mise run sqlc` regenerates it, and `mise run check` runs `sqlc diff`, which
fails where `internal/db` differs from what sqlc generates; it needs no database.

The schema is goose's migrations in `apps/api/migrations/`, plain SQL that sqlc reads as its
schema too. goose's CLI is pinned in `mise.toml`, and the next migration is made with `goose -dir
apps/api/migrations create -s <name> sql`, which carries on the numbered sequence. The migration
`00001_notes.sql` and the query `ListNotes` are examples of the pattern, a table, a query and the
models sqlc makes: replace them with the product's first real migration and queries before its
first deploy.

## Considered options

- An ORM over sqlc — it writes the SQL, so a query's cost and shape are hidden behind code, and
  the schema is described twice.
- `chi` as the router — a library to pin for one route the standard library routes as well.
- golang-migrate or atlas for migrations — golang-migrate splits each migration into two files,
  and atlas plans changes from a declared schema, a step more than plain SQL that sqlc reads.
- A check of the database in `GET /api/up` — the server would answer as down while it can still
  serve, and the check needs a database; a product that wants one adds its own route.
- `hathi doctor` in the check — it reports Git hooks that aren't on, and in CI they never are, so
  check would fail for a reason that isn't the code's.
- Git hooks in `.git/hooks`, written per clone — untracked, so a teammate's clone has none until
  someone writes them, and two clones drift.
- Tools installed by each person, or versions left floating — a tool's new release breaks one
  machine or CI and not another.

## Consequences

- Each clone needs git and mise; mise installs the rest.
- A commit or push fails where `hathi` isn't installed, so `mise run setup` comes first.
- Raising a tool's version is an edit to `mise.toml`, and CI runs the new one with it.
- A change to `queries/` or `migrations/` is followed by `mise run sqlc`, or check fails.
- Raising Go's version is an edit to `mise.toml` and to `apps/api/go.mod`'s `go` directive, and
  golangci-lint may need raising with it, since it refuses a module newer than the Go it was built
  with.
