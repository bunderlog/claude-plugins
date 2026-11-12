# Session start names every decision, requirement, Issue and term the project keeps

## Problem

Claude starts each session knowing only that `.about/` exists, so it edits code without the ADR or
PRD the change rests on: of 52 edits on this machine from 2026-10-01 to 2026-11-02 to a file an ADR
or PRD names, or a path of two or more segments ending in its folder (`entities/deviceConfig`), it
was read earlier in the session, or by a subagent of it, before 20; in webui before 0 of 22, in the
other five projects before 20 of 30. A rule that waits to be read is read rarely, as the Guidelines
were (5 of 79), and one in the context at the moment of a decision is followed (15 of 22, ADR
measurement). The titles of the ADRs and PRDs already state their decisions, so a list of them
costs little: about 3,200 characters in this repo, the largest of the machine's projects.

## Users

- Claude, in every session of a project that turns baloo on, and the person, who reads it to
  answer "what did we decide about X" without opening files.
- Not for: a project that keeps its PRDs or Issues in a tracker, whose pages session start doesn't
  list (ADR issues, ADR prd).

## Success signal

Counted as on 2026-11-02 (ADR measurement), on the sessions of the month after the Release: of the
edits to a file an ADR or PRD names, the share where it was read earlier in the session rises from
20 of 52 to more than half, and above 0 in webui.

## Scope

- In a repo where baloo is on, session start puts in Claude's context, derived from the working
  tree each time (uncommitted files too) and kept in no file of its own:
  - each ADR, the `*.md` files directly in `.about/adr/`, a line each: its file name without
    `.md` and its title, the first line outside a fenced code block that starts with `# `, as
    written; the folder named once, above them;
  - each PRD in `.about/prd/` and each Issue in `.about/issues/`, the same way;
  - the terms of `.about/glossary.md`, each line outside a fenced code block that starts with
    `**<name>**:`, by its name alone, on one line;
  - one line telling Claude to read the ADR, PRD or Issue a task touches before its first edit,
    and to say where the code already breaks it, where any is listed, and to use the glossary's
    words, where it has terms. With the titles alone Claude read only the ADRs that fit and less
    code, and missed code that breaks one (eval case `adr/code-contradicts-adr`, 2026-11-12: 0 of
    3 on Sonnet, 3 of 3 without the plugin; with this clause 2 of 3, and 3 of 3 on Opus).
- A kind with nothing to list is left out, and so is the whole index where no kind has anything.
- The index stops at 8,000 characters: each kind it didn't reach in full, in the order above,
  ends with a line saying how many it left out and their folder or file.
- It prints in headless sessions too, and nothing where session start already prints nothing:
  outside a repo, in the home folder or Claude Code's own, in a Session review's session.

## Non-goals

- Giving the index to a subagent or a Workflow's agents: the verifier and the planner read the ADRs
  themselves (ADR verify).
- Linking ADRs and acceptance criteria to code, so the plugin gives the one a touched file needs.
- The Inbox's titles: session start counts its items, and `/baloo:inbox` goes through them.
- Rewriting a project's ADR titles that name a subject rather than a decision ("Annual billing"):
  the `adr` skill's work, when the ADR is next changed.
- PRDs and Issues kept in a tracker.

## Anti-goals

- Claude takes a title for the whole decision and edits against what the ADR's body says.
- The index crowds out what session start says today: the Inbox's count and the uncommitted files
  in `.about/` stop reaching Claude, or reach it cut.

## Acceptance criteria

- In a repo with a copy of this repo's `.about/` of 2026-11-10 (24 ADRs, 12 PRDs, 28 terms),
  session start names each ADR and PRD by file name and title and each term, and the index,
  from its first line to its last, is under 4,500 characters.
- An ADR added as `.about/adr/new.md`, uncommitted, with the heading `# Something is decided`
  shows in the next session start as `new` with that title, and session start writes no file in
  the repo, `HOME` or `CLAUDE_CONFIG_DIR`.
- An ADR whose file has no `# ` heading outside a fenced code block is named by its file name
  alone; a `**Term**:` line inside a fenced code block of the glossary isn't a term; a file in a
  subfolder of `.about/adr/` isn't listed.
- A repo with only `.about/glossary.md` gets its terms and the line about the glossary's words,
  and no ADR, PRD or Issue line; a repo with `.about/` empty, or none, gets no index.
- In a repo with 300 ADRs of 80-character titles, the index ends by 8,000 characters with a line
  naming how many ADRs it left out and `.about/adr/`, a line for the PRDs and the terms it didn't
  reach, and the Inbox's count and the uncommitted files after it in full.
- Run with `BALOO_SESSION_REVIEW` set, or in the home folder, session start prints nothing; run
  with `CLAUDE_CODE_ENTRYPOINT=sdk-cli`, it prints the index.
