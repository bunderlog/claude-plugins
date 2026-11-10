# Writing for agents

For anything an agent reads: a skill, a CLAUDE.md or AGENTS.md, a prompt, a hook's output.

## 1. Pay for context once

- What loads every session costs every turn. Keep it to rules that must always hold and to
  pointers; put the rest in files read when needed.
- A pointer names the task that calls for the file, first: "Writing tests: `testing.md`". When
  the file gets missed, sharpen the trigger before moving its content up.
- A file read on demand still competes for attention: split one that serves unrelated tasks.

**Test:** everything always loaded is needed on most tasks.

## 2. Say it once

- One rule, one place; elsewhere, point to it. Copies drift.
- Leave out what the agent can look up (scripts, config, `--help`); write down what it can't:
  the reason, the unwritten convention, the trap.
- One word per concept, the project's own; define a word the reader won't know.

**Test:** changing a rule is a one-place edit.

## 3. Cut what changes nothing

- Delete a line the model follows anyway; check by running without it.
- Delete whole sentences, not words from them.
- Remove a line as soon as it stops being true.

**Test:** every line changes what the agent does.

## 4. Make each step checkable

- End each step on something the agent can observe: a command's output, a file that exists, a
  list with every item handled. "Understand the code" has no end.
- If the agent rushes a step to reach the next, hand the next to a separate session or subagent.

**Test:** the agent can tell, without asking, whether a step is done.

## 5. Ask for what you want

- State the behavior: "one-line comments", not "no long comments". A ban names what it forbids.
- Keep a ban only as a guardrail, paired with what to do instead.
- A word the model already knows well (_tracer bullet_, _red_, _tight_) carries more than a
  paragraph.

**Test:** each instruction names what to do.

## 6. Enforce what must hold

- Text can be skipped. A rule that must hold goes into a hook, a check or a test; failing that,
  a permission or setting; text last.

**Test:** every rule whose breach costs real work is checked by something other than the agent.
