# The skills are measured by eval suites in `evals/`, run by hand with `claude plugin eval`

Date: 2026-11-01

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

On 2026-11-01 `prd`, `issue`, `interview` and `tidy` got cases, each failing without the plugin on
Opus and Sonnet. `architecture`'s, a pass-through an ADR keeps on purpose, scored 1.00 both ways on
both and was dropped: Claude reads `.about/adr/` before proposing a refactor anyway. `prd`'s
fresh read found the gap on Sonnet in 1 of 3 runs, where Opus found it in 3 of 3.

A case on a design proposal, such as `contradicts-adr`, `code-contradicts-adr` or
`open-question`, measures the plugin as a whole, not `adr`: on 2026-10-20 the skill loaded in
none of their runs on Opus or Sonnet, and the plugin's Guidelines and session start still scored
1.00, where each case fell below that without the plugin on one model or both. `adr` loading
there is not a goal, so `skill-fired` in them only reports; a case that has failed without the
plugin on one model, as `code-contradicts-adr` did on Sonnet, stays.

The Session review's prompt is the exception to keeping a case only once it fails without the
plugin: the prompt is the plugin's text, built by its code, and a case gives it to Claude in either
arm, so the arm without the plugin would measure the `adr` and `glossary` skills, not the prompt.
Its cases in `evals/session-review/`, named `review-*`, run with the plugin only (`mise run
eval-review`, `--ablation none`) as a guard against a regression of the prompt: a decision agreed
and not recorded is proposed as an ADR, one already recorded proposes nothing, a choice left open
is an Inbox item. Each case's `prompt.md` is written by `evals/session-review/prompts.py` from
`review._prompt` and the case's `conversation.md`, so it asks what a review is asked; run it after
the prompt changes.

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
- A case on a design proposal where only `adr`'s Probe gets the answer right — it would test the
  skill's Check and Probe, which no case does, but waits for a session where Claude took a
  design unchecked.

- The Session review's prompt measured against a short prompt in a second arm ("propose changes
  to .about/") — it would show what the prompt adds, for twice the runs and a baseline nobody uses.

## Consequences

- Nothing makes anyone run the suites: a skill's text can change without them.
- A score depends on the model: a drop after a model changes is not a regression of the text.
- A run of the suite costs about $0.50 to $1 a case on each model.
- `mise run eval` runs the `review-*` cases too, with an arm without the plugin that measures
  nothing: `--case` takes no pattern to leave them out.
- Revisit when a regression a suite would have caught reaches a Release, or CI can run them cheaply.
