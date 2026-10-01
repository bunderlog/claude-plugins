---
name: prd
description: Write and keep a feature's PRD — the problem it solves and for whom, how success shows, its scope and non-goals, and the acceptance criteria it is tested against — when the user asks for a PRD, requirements or acceptance criteria, a feature's agreed purpose or scope changes, or a feature is built and its criteria need checking against its tests. Challenges vague goals and criteria no test could check, checks them against the glossary and ADRs in .about/, and keeps one .about/prd/<feature>.md per feature, or a page in the tracker the project names, edited in place. Not for how to build it, or for settling a plan's decisions.
---

# PRD

You are agreeing with the user what a feature is for, not taking notes. Make every part
checkable; don't just agree.

## Where

`.about/prd/<feature>.md` at the git repo's root — one feature per file, as agreed now
([format](format.md)) — unless the project's CLAUDE.md or AGENTS.md names a tracker for PRDs (a
Confluence space, Notion, a Jira epic). Then each PRD is a page there in the same format, written
through that tool's connector and naming its epic, and none is kept in the repo. Without that
connector, or without access through it, stop: say which connector to set up, and offer the
PRD's text here. Write no issues; stories link to the PRD. If `.about/prd/` still holds PRDs
once a tracker is named, offer to publish each there and delete its file when the user confirms.

Read the existing PRDs, `.about/glossary.md` and `.about/adr/` before you start, and the code the
feature touches. The project's own conventions (another folder, a template) win.

A list of decisions the user confirmed earlier in the conversation is settled: take its answers,
don't ask them again.

## Probe

Challenge each part until it holds:
- **Problem** — whose pain, in a sentence, apart from any solution: "add CSV export" is a
  solution; "support retypes every report into Excel" is the problem.
- **Success signal** — what moves, from what to what, by when; or the qualitative signal when
  nothing can be measured. "Users like it" is neither.
- **Scope** — the smallest version that solves the problem. Name the Non-goals: what someone
  will assume is included and isn't.
- **Acceptance criteria** — each one a test can pass or fail: the situation, the action, the
  expected outcome ("an export of 10,000 rows finishes within 5 s"). Rewrite "fast", "simple"
  or "robust" as one.

Test the criteria with borderline cases: nothing, too much, a failure halfway, someone who may
not do this. A word the glossary lacks or uses differently, or a criterion that contradicts an
ADR, is a finding: name both sides and ask which holds.

## Built

Once code for the feature exists, link each criterion to the test that checks it:
`→ test: <file> "<test name>"`, the file under its repo's name in a tracker's PRD
(`webui/src/export.test.ts`). A criterion with a link is built; one without is not yet. Check
every link in the repo you are in: the test exists and checks what the criterion says; list the
other repos' links as not checked from here. A criterion with no test, a link to a test that's
gone, or code that does something else is a finding: name it and ask whether the criterion or the
code is wrong; don't rewrite a criterion to match the code.

## Ask

Ask the open points a few at a time with the AskUserQuestion tool: each question says in a line
why it matters; each option, two or three concrete ones, gives its trade-off; your
recommendation comes first, marked "(Recommended)". Without the tool, write each question with
its options and `→ Recommended: <option>, because <reason>`.

## Record

- Write the file once the problem and success signal hold, with `Status: proposed` while any
  part is open; what's still undecided goes under Open questions.
- Drop the Status line when the user agrees every part and no question is left.
- When the purpose, scope or criteria change, edit the PRD in place; git or the tracker keeps
  the earlier text.
- Tell the user in one line what changed.
