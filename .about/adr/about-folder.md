# Project knowledge lives in `.about/` at the repo root

Date: 2026-10-07

The skills keep a project's glossary, ADRs, PRDs, Inbox and Issues in `.about/glossary.md`,
`.about/adr/`, `.about/prd/`, `.about/inbox.md` (ADR inbox) and `.about/issues/` (ADR issues), at
the root of the git repo the session is in, whatever folder it was opened in. It is project
knowledge for people and for any agent, so it belongs neither in one vendor's config folder nor in a
folder other tools already claim; `.about` is short, unclaimed, and sorts first. A monorepo has one
glossary, with a context per project, and one ADR log. The Session review runs at the same root and
proposes changes only to what is there, in `.about/proposals/` (ADR session-review). A project with
its own conventions (`CONTEXT.md`, `docs/adr/`, numbered ADRs) keeps them: the skills follow the
project.

Every role, product and testing too, works with this knowledge through git alone, in a clone of
the code repo: there are no roles without git, and no MCP server or other store holds it. baloo
targets Claude Code on such a clone, not Cowork, where its Hooks are unreliable, nor cloud
sessions of Claude Code.

## Considered options

- `docs/` — mixes the glossary and ADRs with general documentation.
- `.claude/` — Claude Code's own configuration; ties the knowledge to one tool.
- `.agents/` — neutral, but shared with Codex, Copilot and others, which claim parts of it.
- `.kb`, `.knowledge` — fine, but don't sort first.
- The folder the session was opened in — each project of a monorepo gets its own, but where the
  files land depends on how the session was opened, and a session in a subfolder never finds the
  repo's.
- For roles without the code repo: a repo of `.about/` alone, a store such as Notion through MCP,
  an MCP server over the knowledge repo, or GitHub's MCP over the code repo — every role works in
  a clone, and an MCP server has no session's end for a Session review.
- Cowork or claude.ai/code for people with no git or terminal — baloo needs its Hooks, which
  Cowork runs unreliably.
- An `onboard` skill, a tour of the project for someone new — Claude already answers that as a
  question with `.about/` at hand.

## Consequences

- The folder is hidden: point to it from `AGENTS.md` or `CLAUDE.md`.
- Moving the default later means migrating every project that uses it.
- An `.about/` in a subfolder is ignored; move it to the repo root.
- A git worktree or a submodule has its own root, so its own `.about/` unless it is committed.
