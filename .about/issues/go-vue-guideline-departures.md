# Bring a fresh go-vue repo in line with louie's Guidelines

2026-11-10

## Symptom

A repo fresh from `/louie:new` departs from louie's own Guidelines in a few small places, so
the first verifier run on any new product reports them, and an agent copying the template's code
copies the departures too. Fix them in the template now, while it has one route and two
components, before products built on it multiply them.

## Evidence

- A verifier run against louie's Guidelines on a repo fresh from `/louie:new` (0.49.0) found these,
  after the one that blocked was fixed in 0.49.1:
  - `apps/api/internal/handler/handler.go`: the `ServeMux` answers an unknown `/api/` path or a
    wrong method with its own plain-text 404 or 405, not `respond`'s JSON (`go` §3).
  - `apps/app/src/app/App.vue` and `apps/app/src/views/HomeView.vue` open with no comment, where
    every `.ts` file does (`typescript` §5).
  - `CLAUDE.md.tmpl` restates what `mise.toml`'s `setup` task runs, and asks for `mise run check`
    before a push, which no hook runs and CI already does (`writing-for-agents` §2 and §6).
  - `apps/api/internal/database` beside sqlc's `apps/api/internal/db`: two packages named for one
    thing (`go` §1).
  - `apps/api/internal/handler/app_test.go:31`: the test helper `get` takes no `t` (`go` §4).

## Acceptance criteria

- In a repo fresh from `/louie:new`, `GET /api/nope` answers 404 with `Content-Type:
  application/json` and a body `{"code": "not_found", "message": …}` written by `respond`.
- In that repo, `POST /api/up` answers 405 with an `Allow: GET, HEAD` header and a JSON body
  `{"code": "method_not_allowed", "message": …}` written by `respond`; `GET /api/up` still answers
  200 with `{"status": "up"}`.
- A path outside `/api/` is still the app's, as `WithApp`'s tests have it.
- Every `.vue` file in the template opens with a comment saying what it is.
- `CLAUDE.md.tmpl` names `mise run setup` without listing what it runs, and no longer asks for
  `mise run check` before a push.
- `apps/api/internal/` has one package for the database: `database.Open` lives in sqlc's
  `internal/db` as a hand-written file beside the generated ones, `internal/database` is gone,
  and `mise run check`'s sqlc drift check still passes.
- Every test helper in the template's Go takes `t` and calls `t.Helper()` first.
- `mise run check` passes in a repo fresh from `/louie:new`, as CI makes it.

## Comments

### 2026-11-10 · fix option

The 404 and 405: a catch-all `/api/` route answers the 404 through `respond.Error`; for the 405,
`ServeMux` writes its own reply when a path matches under another method, so either each path is
registered without a method and its handler switches on the method, or a small wrapper replaces
the mux's plain-text 404 and 405 with `respond`'s JSON, keeping the `Allow` header. The wrapper
keeps `Routes` reading as one line per route; the switch needs no response capture.

### 2026-11-10 · decision

The wrapper: when `mux.Handler(r)` finds no pattern, the mux's own 404 and 405 go out through
`respond.Error`, with the `Allow` header the mux set. Routes keep their method patterns, one line
each, a route a product adds needs no method handling of its own, and `Allow` stays right by
itself. No catch-all `/api/` route: a method-less `/api/` pattern takes `POST /api/up` and answers
404 instead of 405.

### 2026-11-10 · fix option

The database package: `Open` moving into `internal/db` gives one name, at the cost of a
hand-written file in a folder sqlc generates into; sqlc writes only its own files there, so it
survives `sqlc generate`. Renaming `internal/database` to `internal/postgres` keeps generated and
hand-written code apart, but leaves two packages about the database. The first is chosen.

### 2026-11-10 · left out

`cmd/server/main.go` reads its three settings (`DATABASE_URL`, `APP_DIR`, `ADDR`) itself. A
`config` package (`go` §1) comes due as the settings grow, not at three, so it isn't part of this
Issue.
