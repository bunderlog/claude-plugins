# The skills are measured by eval suites in `evals/`, run by hand with `claude plugin eval`

Date: 2026-10-19

Nothing measured whether a skill's text makes Claude follow it: the tests cover the plugin's code,
and the measurement of 2026-10-07 (ADR measurement) read sessions, which show whether a part was
used, not whether a skill works. So the skills, the agent and the Guidelines get eval suites, run by
Claude Code's `claude plugin eval`, which scores each case with the plugin and without it, so a
suite shows what the plugin adds. `adr` comes first.

A case is written before the text it tests, and kept only once it fails without the plugin: what
Claude does anyway needs no text. Each case pins one thing a skill promises beyond the bare model,
such as `adr` editing an ADR in place when a decision changes, and is graded by a regex over the
file it produces where it can be, as a judge's verdict varies from run to run. Whether a skill
loads on a user's phrasing and what it does once loaded are separate cases. A case runs at least
3 times an arm, on the default model and on Claude Sonnet: on 2026-10-19 the same plugin scored
0.00 with and 1.00 without on Sonnet, where Opus scored 1.00 both ways, and the cause was a
Guideline, not the skill (ADR guidelines). A line of a skill that no case fails without is a
candidate for deletion.

`adr`'s first case, a proposal that breaks an ADR, failed without the plugin on Sonnet but not on
Opus, which checks `.about/adr/` on its own; it stays, as the regression the suite caught. Its
second, a decision that changes an earlier one, failed without the plugin on both: the bare model
wrote a new ADR beside the old one.

The suites live in `evals/` at the repo root, outside the plugin: an install doesn't carry them,
and a change to one needs no Release (ADR releases). `--eval-dir` takes no path outside the plugin,
so they run from the repo's root, each case naming the plugin in its `plugins:`, which may only
point under the folder a run starts in. They run by hand, as `mise run eval`, which grants Write
and Edit, when a skill's text changes, not in CI: each run makes real model calls, and CI would
need an API key.

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
- A case kept though it passes without the plugin on every model it runs on — `adr`'s first
  scored 1.00 both ways on Opus, which shows nothing the plugin adds.
- A description that loads `adr` on any design question — it fired in 1 of 3 runs instead of 0,
  and the answer was right either way.

## Consequences

- Nothing makes anyone run the suites: a skill's text can change without them.
- A score depends on the model: a drop after a model changes is not a regression of the text.
- A run of the suite costs about $0.50 to $1 a case on each model.
- Revisit when a regression a suite would have caught reaches a Release, or CI can run them cheaply.
