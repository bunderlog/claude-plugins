# The skills are measured by eval suites in `evals/`, run by hand with `claude plugin eval`

Date: 2026-10-14

Nothing measured whether a skill's text makes Claude follow it: the Go tests cover the binary, and
the measurement of 2026-10-07 (ADR measurement) read sessions, which show whether a part was used,
not whether a skill works. So the skills, the agent and the Guidelines get eval suites, run by
Claude Code's `claude plugin eval`, which scores each case with the plugin and without it, so a
suite shows what the plugin adds. `adr` comes first: its rule never to contradict an ADR silently
is the easiest to grade, given a proposal that breaks one.

The suites live in `evals/` at the repo root, run with `--eval-dir`, outside the plugin: an install
doesn't carry them, and a change to one needs no Release (ADR releases). They run by hand, as
`mise run eval`, when a skill's text changes, not in CI: each run makes real model calls, and CI
would need an API key.

## Considered options

- Suites in `plugins/baloo/evals/`, where `claude plugin eval` looks by default — no flag, but
  every install carries them.
- Running them in CI on each change to a skill — catches a regression on every PR, for an API key
  secret and tokens on each run.
- Running them before each Release, from `mise run release` — never forgotten, but a Release waits
  on model calls, and a flaky grader blocks it.
- Sessions and `retro` alone — they show a rule broken only after it cost a session, and nothing to
  compare with.
- `inbox`, the verifier or the Guidelines' index first — checkable too, but `adr`'s rule is the
  clearest pass or fail.

## Consequences

- `mise run eval` and the `adr` suite are still to write.
- Nothing makes anyone run the suites: a skill's text can change without them.
- A score depends on the model: a drop after a model changes is not a regression of the text.
- Revisit when a regression a suite would have caught reaches a Release, or CI can run them cheaply.
