# PRDs have a skill of their own, one per feature in `.about/prd/` or the project's tracker

Date: 2026-10-01

The `prd` skill writes and keeps a PRD per feature in `.about/prd/<feature>.md`, beside the
glossary and ADRs it is checked against (ADR about-folder). It probes the problem, the success
signal, the scope and the acceptance criteria itself rather than extending the `interview` skill, which
settles how a plan is built, not what it is for. When the conversation already holds a confirmed
decision list, `prd` takes its answers as settled; skills are independent, so neither calls the
other.

A project can keep its PRDs in a tracker instead, named in its `CLAUDE.md` or `AGENTS.md` (a
Confluence space, Notion, a Jira epic). `prd` then writes each as a page there through that
tool's connector, in the same format and naming its epic, and keeps none in the repo: one copy,
where the people who agree it work. The skill text names no tool. Without the connector, `prd`
stops and says which to set up, rather than writing a repo copy meant to move later. It writes no
issues; stories link to the PRD's criteria. When a project moves to a tracker, `prd` offers to
publish each repo PRD there and delete its file.

A PRD is edited in place, as an ADR is (ADR adr-format), with `Status: proposed` while a part is
open and no Status once agreed, and git or the tracker's page history keeps the earlier text. It
stays after the feature ships, as the record of what the feature is for and of the criteria it is
tested against.

Nothing marks a PRD as built. Each acceptance criterion, once built, names the test that checks
it (`→ test: <file> "<test name>"`), so a criterion without one is not built yet, and the links
can't claim more than the tests do. A tracker's PRD can span repos, so its links name the repo,
and `prd` checks those of the repo it runs in. When `prd` is used on a built feature, it checks
every link and names a criterion with no test, a link to a test that's gone, or code that does
something else, asking which is wrong rather than rewriting the criterion to match the code.

The Session review never edits a PRD (ADR session-review): a PRD is an agreement with the user
about what to build, and a change nobody saw costs more there than in a term or a decision record.

## Considered options

- A Guideline in place of the skill (ADR guidelines) — one description less in every session, but
  a Guideline keeps no document, and `/prd` would go for a request nobody mistakes for another.
- `interview` writing its decision list out as a PRD — one skill fewer, but it gains a second job, and a
  PRD could only follow one.
- The tracker by default — suits product and QA, but no project could use `prd` before setting
  up a connector.
- A Config key naming the tracker — checked by the schema, but the Config holds the plugin's
  Checks and settings, and `prd` is a skill that already reads the project's `CLAUDE.md`.
- Naming Confluence and Jira in the skill — sharper for Atlassian teams, but leaves the others
  out.
- A repo copy while the connector is missing — two places to look, and a copy that may never
  move.
- `prd` creating a story per criterion — the criteria in two places, drifting apart.
- A PRD per repo for a feature spanning several — one agreement split across pages.
- `docs/prd/` — easier to find for people outside the dev team, but mixed with general
  documentation (ADR about-folder) and apart from the glossary and ADRs it is checked against.
- Deleting a PRD once its feature ships, its lasting parts moved into tests and ADRs — loses why
  the feature exists, and the criteria QA tests it against.
- A frozen PRD, each change a new one — a chain to read, as ADR adr-format found for ADRs.
- The Session review keeping draft PRDs up to date — an unattended change to what gets built.
- "Spec" or "Brief" for the document — a spec reads as a technical design; a brief undersells the
  acceptance criteria.
- A `Planned` trailer, removed once the feature ships — one line, but it goes stale the day
  someone forgets it, where a missing test link shows itself.
- A Check failing a commit whose PRD names a test that doesn't exist — enforced, but test names
  are written differently in each language.

## Consequences

- A tracker's PRD is checked against a repo's glossary, ADRs and tests only from a session in
  that repo.
- A PRD has no Date line and no Check like `no-stale-adr-date`: only `prd` edits one, with the
  user there, and git records when.
- A PRD falls behind the code unnoticed until `prd` is used on its feature, which checks the
  links. Revisit the Check on test links when teams leave criteria unlinked, and the Session
  review's limit when PRDs keep going stale.
