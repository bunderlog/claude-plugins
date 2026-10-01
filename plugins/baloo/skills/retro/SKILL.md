---
name: retro
description: Review how past sessions went and recommend changes to the project's setup (CLAUDE.md, the baloo Config, settings, skills, hooks) that would have spared the trouble — when the user asks for a retro, what went wrong in a session, or how to improve the setup from experience. Condenses the transcripts, ranks stalls by cost, and changes only what the user picks. Not for recording terms or decisions.
---

# Retro

Look at how the work went, not at what it produced. Every stall cost the user something; the
fix belongs in the setup, so the next session doesn't pay it.

## Read

From the project folder, run
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' sh '${CLAUDE_PLUGIN_ROOT}/scripts/loader' condense`: no
argument for the latest session (the current one, if it is running), `--last <n>` for more,
or session ids. Read its output in full: prompts, commands, interrupts and failed tool calls with
their `[line]`, repeated calls, expensive calls, and for several sessions a summary of failures by
kind, repeated prompts and the tokens each tool added to the context. To check one moment, run it
with `<id> --around <line>`: the lines around it in full, masked. Read transcripts only through it:
a raw one can hold a secret an earlier session printed.

Then read what a fix would touch: CLAUDE.md, the Config (`.claude/baloo.yml`),
`.claude/settings.json`, the hooks and skills involved, and the project's auto-memory
(`MEMORY.md` and its files, in the project's folder under `~/.claude/projects/`). A fix that
already exists but is off, not wired up or broken is the thing to report, not a new one. A
project where no Git hook or CI job runs its lint and tests is a finding too: report it with the
stalls such a check would have caught.

## Look for

- **Refused calls** (`classifier`, `permission`, `rejected`): the rule or mode that would have
  let a safe call through, or the reason it should never have been tried.
- **Failed commands** (`exit`): a real failure, or a misused tool or shell (a glob with no
  match, `=word` in zsh, a wrong path)? Misuse that recurs needs an instruction or a check.
- **Denials by a Check** (`check`, named by its `baloo:<check>:`): a real danger, or a false
  alarm — a bug in that Check.
- **Interrupts and corrections**: what Claude did that the user stopped or redirected, and what
  would have told it beforehand.
- **Repeated prompts**: work the user keeps asking for by hand — a skill, a hook or a Git hook.
- **Repeated calls**: Claude hunting for the same thing — a pointer in CLAUDE.md.
- **Expensive calls**: a call that filled the context — a whole file read where a part would do,
  a command's full output, an MCP server whose calls spend many tokens — a narrower command in
  CLAUDE.md, an output cut by a flag or a pipe, or an MCP server turned off where it isn't used.
- **Missing information**: Claude guessing, or asking the user for a log or a state it couldn't
  read — a server log teed to a file, read-only access to the service, or an MCP server.
- **Workarounds in memory**: an entry that patches a skill, a CLAUDE.md line or a setting (a tool
  that fails, and what to do instead). Move the fix into what it patches and drop the entry: a
  teammate's session never sees this memory, and the broken skill stays broken.

A failure that is part of the work (a red test mid-change), a denial that was right, or a prompt
that is the user's own call each time ("commit it") is not a stall. Rank stalls by cost: how
often, times what each cost the user (a retry, a mode switch, a wrong turn undone). Mention a
one-off only if it was severe.

## Fix where it holds

Prefer the fix that works without Claude remembering it:
1. **Enforced**: a Check turned on in the Config, a test, or a lint or Git hook the project owns.
   A mistake with a fixed pattern (a banned API, an import shape, a file in the wrong place)
   always gets one, never a written line.
2. **Configured**: a permission rule or a setting of Claude Code.
3. **Written**: the shortest line that changes behavior — in CLAUDE.md for this project,
   `~/.claude/CLAUDE.md` for every project, or a skill. Cut an instruction the transcripts show
   had no effect.

Say where each fix lives: this project, or a plugin or Claude Code itself. A fix to baloo (a
Check's false alarm, a skill's rule) is an issue to file on `bunderlog/claude-plugins`, written
out for the user, unless this project is baloo's own repo; one to Claude Code or another plugin
is a report to send. Neither is a change to their installed copy.

## Report

A ranked list of stalls; for each: what happened (session, `[line]`, how often), what it cost,
the fix (which file, what change). Ask which to apply, apply only those, and run the project's
checks. Each fix not picked, unless the user drops it, becomes an item in `.about/inbox.md`: a
`## <title>`, a line `<YYYY-MM-DD> · retro`, then the stall and the fix; create the file,
`# Inbox` first, with its first item. Don't commit. Replace secrets you quote with `*****`.
