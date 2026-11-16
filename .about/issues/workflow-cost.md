# Show what each of louie's Workflow runs took, and count its cost in the Assessment

2026-11-16

## Symptom

Nobody sees what a run of `/louie:plan`, `/louie:deliver` or `/louie:verify` costs: Claude relays
its result alone, and the Assessment counts no Workflow. To start optimizing the Workflows, which
phase costs most has to be known, run after run.

## Evidence

- The task-notification of each run already holds `<usage>`: `subagent_tokens`, `tool_uses`,
  `duration_ms` (the plan of Issue assessment-every-plugin: 104,544 tokens, 25 tool calls, 4.4
  minutes, 1 agent); Claude's reply didn't name them.
- Each agent's Transcript, `<session>/subagents/workflows/<run>/agent-<id>.jsonl`, has each
  message's `model` and `usage` (input, output, cache written, cache read), and its
  `agent-<id>.meta.json` its `agentType` and `workflowPhase`.

## Acceptance criteria

- PRD delivery's criterion: a louie Workflow's result is given with the run's tokens, agents and
  minutes.
- PRD assessment's criterion: a `plan` run's cost from its agent's tokens at its model's prices,
  Plan its costliest phase, and a model with no price counting tokens only.

## Comments

### 2026-11-16 · fix option

The Guideline: one line among the rules `principles` prints whole on every task. The cost: in
`assess.py`'s Workflow figure, which Issue assessment-every-plugin adds; this is built after that
Issue's pull request is merged, as both change `assess.py` and `condense.py`. The prices are a
table in bagheera, by model id, with the date they were read from Anthropic's price list.
