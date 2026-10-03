## Guidelines for more stacks

2026-10-03 · user · kept 2026-10-03

Guidelines beside `go`, `typescript`, `vue` and `tailwind` for `python`, `rust`, `react`, `sql`
(migrations, a schema change that stays backward compatible) and `docker`. Settled by deciding
which stacks get one, each with its stack detection for a new Config, or none. Kept to write
each when a project in that stack takes up baloo.

## Guidelines for concerns across stacks

2026-10-03 · user · kept 2026-10-03

`security` (input, authorization, Secrets in code), `api-design` (versions, compatibility) and
`observability` (logs, errors, metrics) as Guidelines. Settled by deciding which earn a Guideline
of their own rather than rules in `principles` or `design`, and whether a new Config turns them on.
`principles` already asks that a change be observable in production, and the Checks keep Secrets
out of commits and Claude's context; kept until a session shows a gap they leave.
