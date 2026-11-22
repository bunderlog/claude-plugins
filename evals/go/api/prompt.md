---
description: New Go code takes the UUIDs the Go it declares ships, wires the routes in main, and logs with the request's context.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Write, Edit]
---

Add the monitors API to the service: `POST /monitors` takes `{"url"}`, gives the new monitor a
UUID as its id and returns it with 201; `GET /monitors/{id}` returns one, or 404 when there is
none. Put the handlers in `internal/handler/monitors.go`, wire the routes in `cmd/api/main.go`,
and log an internal error before answering it. Write the tests in
`internal/handler/monitors_test.go`.
