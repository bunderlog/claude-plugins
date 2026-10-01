# Go

For writing Go: the choices where more than one would be reasonable. These are defaults for
new code: in an existing codebase, its documented conventions and the pattern its code already
follows win.

## 1. Layout and dependencies

- `cmd/<app>/main.go` wires things up and nothing else. The rest lives in `internal/`, one
  package per concern (`handler`, `respond`, `config`, `worker`), named for what it provides,
  never `util` or `common`.
- The standard library first, then a small library per need: a router (`chi`), a driver
  (`pgx`), `sqlc` for queries. No ORM, no framework. Generated code is never edited by hand.

**Test:** every package name says what it's for.

## 2. Errors and logs

- Wrap an error with what failed: `fmt.Errorf("rdap request failed: %w", err)`.
- An error callers must tell apart is a sentinel, `var ErrMonitorLimit = errors.New(…)`,
  checked with `errors.Is`. No `panic` outside start-up in `main`.
- Log with `log/slog`, the `…Context` variants, passing the request's context.

**Test:** every error that reaches a log names the operation that failed.

## 3. HTTP handlers

- A handler type holds its dependencies, built by `NewXHandler(deps)`; each method is an
  `http.HandlerFunc`. Every failure writes its response and returns at once.
- One helper package writes responses: JSON with a stable machine `code` and a human message.
  An internal error gets a generic message, never its detail.
- Request and response bodies are their own small structs with `json` tags; database rows are
  mapped to them, never encoded directly.

**Test:** no handler encodes a response body itself; an empty `204` is the only direct write.

## 4. Tests

- The standard `testing` package, no assertion library. Fail with what was got and what was
  wanted: `t.Fatalf("status = %d, want %d", w.Code, http.StatusCreated)`.
- Name a test `TestThing_Behavior`; table cases run as `t.Run` subtests; a helper takes `t`
  and calls `t.Helper()` first.
- A service you don't own is faked with `httptest.NewServer` behind its client.

**Test:** a failing test's message alone says what broke.
