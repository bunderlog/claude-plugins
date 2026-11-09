# Any project with baloo kept in order with git, Claude Code and baloo alone, for everyone in it

Status: proposed

## Problem

People who work with Claude Code, in many projects or together in one, lose control of them: the
Setup drifts from project to project and from person to person, decisions and open questions are
scattered over several places and don't reach the others, nothing shows which project needs
attention, and each attempt to fix this has brought in one more tool to install and keep up on
every machine.

## Users

- Everyone who works with Claude Code in a project where baloo is enabled, in one project or many,
  on one machine or several. Each gets the project's Setup (`CLAUDE.md`, `.claude/` with its rules,
  settings and Config, and its Git hooks) and its knowledge (`.about/`) from what it commits, keeps
  their own rules and preferences in their own `~/.claude/`, and sees the projects worked on from
  their machine.
- baloo's maintainer, who changes baloo, and how it works with `hathi`, in `claude-plugins`.
- Not for: people without git and a terminal (Cowork), or on Windows.

## Success signal

- A project worked on from this machine that needs attention shows, without opening it, in the
  Status line of a session in any project, for everyone who uses baloo's line; the visibility PRD
  says what needs attention.
- Everyone working in a project gets the same Setup from the repo.
- What one person's session decides or leaves open in a project reaches the others through
  `.about/`, the project's tracker or its Inbox, once that person accepts, commits and pushes it.

## Scope

- This PRD builds nothing itself: its criteria are met through the PRDs named under Non-goals and
  through changes to baloo, each with a PRD of its own.
- Required: git, Claude Code and baloo, with the `python3` 3.9 or later baloo runs on, which macOS's
  Command Line Tools and most Linux distributions ship (ADR binary). Anything else (mise, `hathi`,
  husky, a CI, a tracker) is the project's own choice.
- baloo shares no code with `hathi`: keeping Secrets out of Claude's context and masking them in a
  Retro are baloo's own, with patterns of its own, whether a project has `hathi` or not.
- A project is set up for baloo once the commit checked out holds what the PRD setting a project up
  lists, its Config and Git hooks that check commits for Secrets among them; a clone with no
  committed Config is not set up. The Config and committed settings come only from setting the
  project up, a step whose result someone commits.
- "Once per clone": a clone is told once, and again only when it is cloned anew.
- Every kind of fact has one place, where it is read when it matters:

  | Fact | Place | Read |
  | --- | --- | --- |
  | about a person and how to work with them in one project | their Claude's memory of that project | every session there |
  | a person's rules and preferences for all their projects | their `~/.claude/`, written when they ask | every session |
  | a lesson for everyone with baloo | the baloo Guideline on its subject, `principles` for any task | when its task comes up |
  | why a feature or the product exists and what it does, with its decisions about what | `.about/prd/`, or the tracker the project's `CLAUDE.md` names | in the project |
  | how something is built, and why that way | `.about/adr/` | in the project |
  | what a project term means | `.about/glossary.md` | in the project |
  | what is still to decide | `.about/inbox.md` | through `/baloo:inbox` |
  | work agreed to do | the project's tracker, else `.about/issues/` | by the team |
  | an instruction for Claude in the project, naming the ADR or PRD it comes from | `CLAUDE.md`, `.claude/rules/` | at session start, or when a matching file is touched |
  | a decision about one project's own Setup, such as how it runs `hathi` | that project's `.about/adr/` | in the project |
  | a decision about baloo, `hathi` or how they work together | `claude-plugins/.about/`; `hathi`'s own in its repo | when the Harness changes |

  A Proposal waits on one machine until someone accepts it into its place; the plugin's other
  working files (logs, its data folder) hold no fact of this table.

- The layers and who owns each:

  | Layer | What | Who, where | Takes effect |
  | --- | --- | --- | --- |
  | Commits | message format, no Secrets, no AI co-author, linear history, an ADR's Date set when it changes (a Check the project turns on) | `hathi`, run by the project's Git hooks and CI where it installed it; else the project's own Git hooks, which check for Secrets at least; baloo installs no Git hook | each commit, CI |
  | Claude's commits | the message format Claude writes, no co-author trailer | a line in the project's `CLAUDE.md` that imports the file setting the format (`@.hathi.yml`, which then states the format in full rather than leaning on `hathi`'s defaults, or the project's own); Claude Code's attribution off in `.claude/settings.json` | each commit Claude makes |
  | Session and knowledge | ADR, PRD, glossary, Inbox, Issues, Retro, Session review | baloo | each session |
  | Working rules | Guidelines | baloo, given when a task calls for one | when its task comes up |
  | Session guards | Secrets kept out of Claude's context, and no mark that lets a Secret through a commit Check (`baloo:allow-secret`, `hathi:allow-secret`, `gitleaks:allow`) added by Claude; Git hooks not skipped by Claude's commands (pointing git at the project's own committed hooks is setting up, not skipping) | baloo's Checks in Hooks | each tool call |
  | Project rules | `CLAUDE.md`, `.claude/rules/` with `paths:`, `settings.json` | Claude Code itself, files in the repo | session start; a rule when its file is touched |
  | Outside systems | where tasks and knowledge live outside `.about/` | a line in `CLAUDE.md` | when a skill writes there |
  | Output style | how Claude replies | one of baloo's, picked by the project's Config; a person's own wins | each reply |
  | Personal rules | language, working style, their own Output style or Status line | each person's `~/.claude/` | each session |
  | Visibility | projects needing attention, sessions waiting for their person | baloo's Status line, unless the person set their own (a PRD of its own) | always in view |
  | Harness checks | whether it works: evals, measurements | evals in `claude-plugins`; the measurement's scripts outside it (ADR measurement) | when the Harness changes |

- How baloo, and its work with `hathi`, change: one change at a time, a PRD first for a feature,
  tried in a pilot project from the checkout (`--plugin-dir`) before its Release, and a Release per
  change.

## Considered options

- A second repo for the Harness (`marketplace`, `harness`) — a second home for its decisions, where
  `claude-plugins` already is the `bunderlog` marketplace, named as Anthropic names theirs.
- `hathi`, mise and GitHub required in every project — `webui` had none of them on 2026-11-09.
- A template tool, such as Copier, to bring a Setup into a project — one more tool on every machine,
  for copying a few files a skill can copy.
- More plugins split out of baloo — no one uses a part of it without the rest.
- A visibility page or tool of its own — it would wait to be opened, as the Guidelines waited to be
  read (5 of 79, ADR measurement); the Status line is always in view.
- Lessons for all projects kept in `claude-plugins` — Claude in another project never reads it.
- baloo's own commit Checks where a project has no `hathi` — the same Checks in two places, drifting
  apart.
- A project without `hathi` left with no Secrets check on its commits — a person's commit can leak a
  Secret no session ever saw.
- A commit format written out in `CLAUDE.md` — a second place for `.hathi.yml`'s rules, drifting
  from it. Session start reading `.hathi.yml` — baloo tied to the format of `hathi`'s config.
- An ADR's Date checked by a Hook on Claude's commits — it misses `git add -A && git commit` in one
  call, `commit -a`, scripts and people's commits.
- Session start turning a clone's Git hooks on itself — it would change git's config, which `hathi`
  declined to do too (its ADR hooks).
- Session start writing nothing, the Status line set by hand in `~/.claude/settings.json` — one more
  install step on every machine.
- Session start writing what it writes today (the Config, committed settings, Git hooks) — six
  projects had five different Git hook setups on 2026-11-09.
- baloo's Status line and Output style over a person's own — they replaced what the person chose.
- baloo's version pinned in each repo — a bump in every project at each Release, and a session runs
  the version it started with anyway.

## Non-goals

- Visibility in the Status line, setting a project up, delivery from an Issue to a pull request, a
  new project's rails, and what a PRD and an ADR each hold, a criterion checked by hand included
  (the knowledge skills `prd`, `adr` and `glossary`): each is a PRD of its own.
- Moving existing projects off baloo's Git hooks, its `git-hooks` and `git-hook-commands` keys and a
  committed `outputStyle`, and choosing what checks a project's commits for Secrets where it has no
  `hathi`: part of setting a project up, recorded in that project's ADR.
- `hathi` taking the ADR Date Check over from baloo: a change to `hathi`'s PRD, which today leaves
  it in baloo, made in its repo.
- Rewriting the ADRs this changes (config, git-hooks, checks, adr-format, output-styles,
  status-line, transcripts, binary, doctor, guidelines, evals; prd and about-folder for what a PRD
  and an ADR each hold) and their glossary entries: each changes with the PRD that builds the
  change, and until then describes baloo as it is.
- Replacing a project's own tools: its husky, CI or tracker stay.
- Moving the existing ADRs' decisions about what into PRDs at once: one file at a time, when it is
  next touched.
- Seeing one machine's projects from another, and bringing a person's `~/.claude/` to another
  machine: theirs.
- How a session's decisions become Proposals: the Session review, as it is.

## Anti-goals

- A fix adds a required tool where Claude Code, or what the project already has, would do.
- A fact gets a second place, other than an instruction that names where it comes from.
- More than one feature of baloo, or of its work with `hathi`, is being built at a time, from its
  first commit of code to the Release that ships it; a `fix`, and a PRD such as this one that builds
  nothing itself, aside.
- baloo changes a file of the Setup that git tracks on its own, not at someone's request.
- One person's own rules, paths or preferences reach another through the project's committed files.

## Acceptance criteria

- On a machine with only git, Claude Code and `python3` 3.9 or later, `claude plugin marketplace add
  bunderlog/claude-plugins` and `claude plugin install baloo@bunderlog` are the whole install: a
  session in any git repository other than the home folder and `~/.claude/` then has baloo's skills
  and its Status line, set up for baloo or not, unless the person set their own line. Checked by
  hand on a clean machine.
- In a project with no `mise.toml`, no `hathi`, no GitHub remote and no `gh`, session start and
  `doctor` report no problem that names them (recommending `hathi` is advice, not a problem), and no
  Hook exits non-zero for their absence; a skill may still name one that the project's own choice
  needs, such as `gh` for its CI.
- A session start writes only files git doesn't track and that stay on this machine: the project's
  `.claude/settings.local.json` and `.git/info/exclude`, and the plugin's data folder, leaving any
  of them alone where git tracks it; never a tracked file and never git's config (which
  `info/exclude` isn't).
- In a project with no committed Config, session start says once per clone that the project isn't
  set up, and how to set it up; the Checks in Hooks run there all the same.
- In a clone of a project that commits its Git hooks, where they aren't turned on (the layouts that
  count and the command for each: the PRD setting a project up), session start says once per clone
  how to turn them on, and changes nothing itself.
- In a git repository with no `.hathi.yml`, session start recommends `hathi` once per clone, with
  how to add it, and changes nothing itself.
- A skill writes each fact only to its kind's place in the table: a term to `.about/glossary.md`, a
  decision about how to `.about/adr/`, a feature's why and what to `.about/prd/` or the named
  tracker, agreed work to the named tracker or `.about/issues/`, a question still open to
  `.about/inbox.md`; none writes a fact of these kinds into Claude's memory. Checked by an eval case
  for each kind of fact each skill writes.
- An instruction a skill writes into `CLAUDE.md` or `.claude/rules/` names the ADR or PRD it comes
  from.
- Every `feat` commit under `plugins/baloo/` from 2026-11-10 names a PRD in its body (`PRD
  <feature>`), and every `fix` the PRD, ADR or Issue it brings the code back to; a feature without a
  PRD gets one first.
- In an eval project with `hathi`, set up for baloo, the commit message Claude writes passes `hathi
  check commit-msg` (its `conventional-commits` and `no-ai-coauthor` Checks), run on it after the
  case, without Claude retrying, in two cases: `.hathi.yml` as set up, and with its types changed.
- In each clone of a project set up for baloo, `hathi` or not, whose Git hooks are turned on, a
  commit that adds a made-up AWS access key ID (`AKIA` and 16 random characters from A–Z and 2–7,
  not a published example) is refused by the project's Git hooks, whether a person or Claude makes
  it. Checked by hand.
- In `claude-plugins`, `hathi` and `webui`, once set up for baloo, `doctor` reports no problem with
  what the PRD setting a project up says a project holds. Checked by hand.
- A project's committed Setup files (`CLAUDE.md`, `.claude/`, its Git hooks) hold no absolute path
  into a home folder or a plugin's data folder, and its committed settings set no `statusLine` and
  no `outputStyle`.
- Two people who open the same commit of a project with the same baloo version get the same skills,
  Guidelines, `.claude/rules/` and baloo's Checks in Hooks from it, as session start and `doctor`
  show them, except the rules for their shell and what depends on whether their clone's Git hooks
  are on or `python3` is missing, and unless their own settings turn baloo's Hooks or Guidelines
  off.
- A person who sets their own Output style or Status line in `~/.claude/settings.json` gets it in
  every project from their next session on, also where baloo had set its own in that project's
  `.claude/settings.local.json` before.
- The Release that takes the commit Checks out of baloo ships only once each project the maintainer
  works in is set up for baloo and `hathi` has the ADR Date Check; from it on, a Git hook baloo
  wrote lets each commit through, saying that baloo no longer checks it and how to remove the hook.
