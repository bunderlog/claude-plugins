# Stack: one repository, mise for every tool and task, hathi in the Git hooks and CI, Go with sqlc and goose, Vue with Tailwind in a pnpm workspace

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

`apps/app` is the app, one Vue 3 single-page app in TypeScript, which the Go binary is to serve
from the same origin as the API. Vue because it is the stack its operator already runs, and one app
is enough until a product needs a second. The app follows louie's `vue`, `typescript` and
`tailwind` Guidelines: `src/app/` holds the entry, `App.vue` and the router, and `src/views/` the
pages no feature owns, each loaded when its named route is first visited; a feature gets its folder
in `src/features/` when the first one comes, and code any part of the app uses goes in
`src/shared/` when the first such code comes. Its test sits beside each page: Vitest with
`@vue/test-utils`, mounting it in jsdom. The page fetches nothing yet, so there is no TanStack
Query, Pinia, `cn()` or `cva`; a product adds each when its first need comes.

The JavaScript is a pnpm workspace: `pnpm-workspace.yaml` lists the apps that have a
`package.json`, and `pnpm-lock.yaml` is committed. pnpm because it is stable, refuses an import
the package doesn't declare, and runs Vite and its plugins on the Node they are built against;
Node is on its LTS line. Every package is pinned to an exact version in its `package.json`, and
`minimumReleaseAge` lets a release into the lockfile only once it is two weeks old, a package's
own dependencies too. There are no `scripts` in a `package.json`: `mise run check` runs each tool.

Tailwind styles the app: its classes sit in the markup they style and draw on one theme's tokens,
so a page's look is read and changed in its own file, kept to the theme by the classes there are,
and it is the stack its operator already runs. Tailwind 4 is configured in CSS, in
`src/app/main.css`, with no `tailwind.config.js`: the theme's colors are tokens in `@theme`, each a
pair of a background and the text made for it, and their dark values switch with the system's, so a
component styled with tokens needs no `dark:`.

eslint runs typescript-eslint's type-checked rules, `.vue` files' scripts included, so a promise
left floating fails; then `eslint-plugin-vue`'s `flat/recommended`, and
`eslint-plugin-vue-modular`'s recommended config, which checks the layout and the names, its test
beside a page allowed. Layout of the code is prettier's, at
its defaults with `prettier-plugin-tailwindcss` ordering the classes, and `eslint-config-prettier`
turns off eslint's rules that would fight it. `eslint-plugin-vue-modular` is at 1.26.3: its later
builds don't load in Node, and 1.26.3 loads only through jiti, so eslint's config is
`eslint.config.ts`, which eslint loads through jiti.

`mise run check` installs from the frozen lockfile, then lints, checks the format, type-checks
with `vue-tsc`, tests and builds `apps/app`; it needs no database and no running API.

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
- bun over pnpm — faster, but younger, and Vite's plugins are built and tested against Node.
- npm or yarn — npm lets code import a package it doesn't declare, and yarn's Plug'n'Play needs
  editors and tools set up for it.
- Turbo over the workspace — a cache and a task runner for one app, while mise already runs the
  tasks.
- React — a second stack to run beside the one the operator knows.
- `eslint-plugin-vue`'s `flat/essential` — it drops the recommended rules that aren't about
  layout too, where `eslint-config-prettier` turns off only those prettier owns.
- Scoped `<style>` blocks or CSS modules over Tailwind — each component names its own classes and
  writes its own values, so keeping to the theme's tokens is left to care, and a page's look is
  split between its markup and its styles.
- A component library such as Vuetify — its look is its own, and bending it to the product's
  theme costs more than the few components a product starts with.
- A `tailwind.config.js` — Tailwind 4 reads its theme from CSS, so a JavaScript config is a second
  place for the same values.

## Consequences

- Each clone needs git and mise; mise installs the rest.
- A commit or push fails where `hathi` isn't installed, so `mise run setup` comes first.
- Raising a tool's version is an edit to `mise.toml`, and CI runs the new one with it.
- A change to `queries/` or `migrations/` is followed by `mise run sqlc`, or check fails.
- A change to a `package.json` is followed by `pnpm install`, whose lockfile is committed with it,
  or check fails on the frozen lockfile.
- Raising `eslint-plugin-vue-modular` past 1.26.3 waits for a build that loads in Node.
- Raising Go's version is an edit to `mise.toml` and to `apps/api/go.mod`'s `go` directive, and
  golangci-lint may need raising with it, since it refuses a module newer than the Go it was built
  with.
