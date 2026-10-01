# Project knowledge lives in `.about/` at the repo root

Date: 2026-10-01

The skills keep a project's glossary, ADRs, PRDs and Inbox in `.about/glossary.md`, `.about/adr/`,
`.about/prd/` and `.about/inbox.md` (ADR inbox), at the root of the git repo the session is in,
whatever folder it was opened in. It is project knowledge for people and for any agent, so it
belongs neither in one vendor's config folder nor in a folder other tools already claim; `.about` is
short, unclaimed, and sorts first. A monorepo has one glossary, with a context per project, and one
ADR log. The Session review runs at the same root and edits only what is there (ADR session-review).
A project with its own conventions (`CONTEXT.md`, `docs/adr/`, numbered ADRs) keeps them: the skills
follow the project.

## Considered options

- `docs/` — mixes the glossary and ADRs with general documentation.
- `.claude/` — Claude Code's own configuration; ties the knowledge to one tool.
- `.agents/` — neutral, but shared with Codex, Copilot and others, which claim parts of it.
- `.kb`, `.knowledge` — fine, but don't sort first.
- The folder the session was opened in — each project of a monorepo gets its own, but where the
  files land depends on how the session was opened, and a session in a subfolder never finds the
  repo's.

## Consequences

- The folder is hidden: point to it from `AGENTS.md` or `CLAUDE.md`.
- Moving the default later means migrating every project that uses it.
- An `.about/` in a subfolder is ignored; move it to the repo root.
- A git worktree or a submodule has its own root, so its own `.about/` unless it is committed.
