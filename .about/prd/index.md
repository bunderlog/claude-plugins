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

The index alone, from 0.52.0 (2026-11-10), didn't get them read: in its first six days 6 of 25
such edits came after a read, against 2 of 17 in the six days before. The Guidelines moved the same
way once a Hook gave each at the file it concerns (ADR guidelines), so louie names the ADRs and
PRDs a file concerns when Claude first works on it.

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
- In a repo where louie is on, louie's `PostToolUse` Hook, each time Claude reads, edits or
  writes a file in the repo outside any `.about/` folder, puts in Claude's context the ADRs and
  PRDs that name it, that the Hook hasn't named in the session and that Claude hasn't read with
  the Read tool in it, a line each, `<path from the repo's root>: <title>`, ADRs first, then
  PRDs, each kind by file name; and tells Claude to read them before it edits the file and to say
  where the code already breaks one. It comes in the same added context as the Guidelines the
  Hook gives for that file. It does so in a repo whose `.about/` holds ADRs or PRDs, whether baloo
  is on or not: they are the project's, not baloo's. In a subagent it names nothing and marks
  nothing, and a subagent's Read of an ADR or PRD doesn't count as read: the main thread, which
  edits, is the one to have them. An ADR or PRD names a file where its text holds a path
  of two or more segments (`[\w.@-]+(/[\w.@-]+)+`) that is the file's path from the repo's root,
  or that this path or its folder's ends in after a `/`: the rule `/bagheera:assess` counts the
  Success signal by. Each ADR or PRD is named once a session, a file at most 5, then a line
  saying how many more name it and their folders. It lives in louie, not baloo, since a Hook on a file takes Python
  and baloo has only its `sh` session start (ADR plugin); a project's Setup turns both on.
- A kind with nothing to list is left out, and so is the whole index where no kind has anything.
- The index stops at 8,000 characters: each kind it didn't reach in full, in the order above,
  ends with a line saying how many it left out and their folder or file.
- It prints in headless sessions too, and nothing where session start already prints nothing:
  outside a repo, in the home folder or Claude Code's own, in a Session review's session.

## Non-goals

- Giving the index to a subagent or a Workflow's agents: the verifier and the planner read the ADRs
  themselves (ADR verify).
- Giving an ADR's or a PRD's text at the file, or anything finer than its name and title: which
  acceptance criterion a file serves, or which decision in an ADR.
- Naming the Issues at the file: they name files less steadily, and the index lists them.
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
- In a repo whose `.about/adr/a.md`, titled `# A is decided`, names `src/pay/charge.go`, and whose
  `.about/prd/b.md` names `src/pay`, a Read of `src/pay/charge.go` gives in louie's Hook's added
  context the lines `.about/adr/a.md: A is decided` and then `b`'s, and the words "read" and
  "before" you edit; a later Read or Edit of `src/pay/refund.go` in the same session names no ADR
  or PRD, and the same Read in a new session names `a` and `b` again.
  → test: tests/louie/test_knowledge.py "Names.test_names_once_a_session"
- An Edit or a Write of a file no ADR or PRD names, of a file under `.about/` or a worktree's
  `.about/`, or of a file outside the repo names no ADR or PRD; neither does a Read of
  `src/pay/charge.go` in a session that read `.about/adr/a.md` and `.about/prd/b.md` with the Read
  tool before it.
  → test: tests/louie/test_knowledge.py "Names.test_names_nothing_where_none_is_due"
- A Read of `src/pay/charge.go` by a subagent names no ADR or PRD, and the main thread's next
  Read of it names `a` and `b`; so does one after a subagent read `.about/adr/a.md`.
  → test: tests/louie/test_knowledge.py "Names.test_a_subagent_names_and_marks_nothing"
- The first Read of `src/pay/charge.go` in a repo with a `go.mod` gives the `go` Guideline and
  names `a` and `b` in one added context.
  → test: tests/louie/test_knowledge.py "Names.test_comes_with_the_guidelines"
- A Write that creates `src/pay/new.go`, before any Read in the session, names `b`.
  → test: tests/louie/test_knowledge.py "Names.test_a_write_that_creates_a_file"
- A file 6 ADRs and 1 PRD name gives the first 5 ADRs by file name, then a line saying 2 more
  name it, in `.about/adr/` and `.about/prd/`; those 2 are named at the next Read, Edit or Write of
  a file one of them names, the same file too.
  → test: tests/louie/test_knowledge.py "Names.test_names_five_then_the_rest"
- With `BALOO_SESSION_REVIEW` set, or in a repo with no `.about/`, the Hook names no ADR or PRD.
  → test: tests/louie/test_knowledge.py "Names.test_names_nothing_in_a_review_or_without_about"
