# The `go-vue` template runs with `mise run dev` and deploys with Kamal

2026-11-10

## Symptom

The last of PRD templates' four Issues: `/louie:new` writes `apps/api` and `apps/app` (0.48.0),
but nothing runs them together, the server opens no database, and nothing deploys. This one adds
`mise run dev`, the server's database wiring, the Dockerfile, Kamal's `config/deploy.yml` with
`mise run deploy`, and this repo's CI job running `mise run dev`, which closes PRD templates' first
criterion.

## Evidence

- PRD templates, Scope: `mise run dev` (Postgres in Docker, the API and Vite) and `deploy` (Kamal
  from its pinned Docker image); a Dockerfile and `config/deploy.yml`, the server and registry
  marked for the person; a local database reached with no password; `/louie:new` and the project
  need only git, mise and Docker.
- PRD templates, Acceptance criteria: `mise run dev` answers `GET /api/up` with 200 and serves the
  app's page, checked by a CI job of this repo; only `config/deploy.yml`'s server and registry are
  left marked.
- `~/Projects/chainofsale`: `docker-compose.yml` (Postgres 17 on 5433, with a password),
  `Dockerfile` (the app's build and the Go server, cross-compiled, on distroless), `config/
  deploy.yml` (kamal-proxy with `/api/up` as its health check, Postgres as an accessory), the
  `deploy` task reading `.env`.
- Issue louie-new-api's decision: the database wiring and where migrations run come here.

## Acceptance criteria

- In a repo fresh from `/louie:new`, `mise run dev` starts Postgres in Docker, the API and Vite;
  then `GET /api/up` answers 200 through Vite's address as well as the API's, the app's page is
  served with the product's name in it, and the server has run the migrations. Checked by this
  repo's CI job that makes a repo from the template.
- The local database takes no password: no file of the fresh repo holds one, and `hathi`'s Secret
  Check passes on its first commit.
- The template's Dockerfile builds an image that serves the API and the app's build on one port;
  this repo's CI job builds it.
- `config/deploy.yml` deploys that image with Kamal behind kamal-proxy, `/api/up` its health
  check and Postgres an accessory; its server and registry are the only values left marked for
  the person, and the README says what to fill in and the commands to create the GitHub repo,
  push and deploy.
- `mise run deploy` runs Kamal from a Docker image pinned to an exact version, with the secrets of
  a `.env` the repo ignores; `.env.example` names each secret.
- `/louie:new` and the fresh repo need only git, mise and Docker.
- In this repo, session start still names no stack Guideline that the template's files alone
  would call for, and the template follows louie's Guidelines; its ADR stack says why Kamal and
  the deploy's shape.

## Comments

### 2026-11-10 · decision

Settled before planning, so the plan needn't ask:

- The server opens a pgx pool from `DATABASE_URL` and runs the embedded goose migrations at start
  (`migrations/migrations.go`, `goose.NewProvider`), as chainofsale does, and exits naming what
  failed if it can't; `/api/up` still touches no database. In production it also serves the app's
  build from `APP_DIR`, so one image and one port serve both.
- The local Postgres is `postgres:17-alpine` in a `docker-compose.yml` on port 5433, with
  `POSTGRES_HOST_AUTH_METHOD: trust` and a `DATABASE_URL` with no password in `mise.toml`.
- Vite proxies `/api` to the API in dev; the app itself calls nothing yet, so it still needs no
  TanStack Query.
- The Dockerfile is chainofsale's shape: the app's build and the Go server on the builder's own
  platform, cross-compiled, then `gcr.io/distroless/static-debian12:nonroot`.
- Kamal runs from `ghcr.io/basecamp/kamal` pinned to its latest 2.x release at least two weeks
  old, the SSH agent passed in, as Kamal's docs give it, rather than Ruby and the gem.
- `config/deploy.yml` marks the server and the registry as `<server>` and `<registry>`, with a
  comment pointing to the README; production's Postgres password comes from `.env`, through
  `.kamal/secrets`.
- Any other tool detail with a standard, maintained answer (how mise runs the API and Vite side
  by side, how CI waits for them, the healthcheck's timings) is the plan's to take, recorded as an
  assumption, not a decision for the person.
