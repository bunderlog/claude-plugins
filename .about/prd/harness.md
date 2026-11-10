# Any project kept in order with git, Claude Code and bunderlog's plugins alone, for everyone in it

## Problem

People who work with Claude Code, in many projects or together in one, lose control of them: the
Setup drifts from project to project and from person to person, decisions and open questions are
scattered over several places and don't reach the others, nothing shows which project needs
attention, and the tools brought in to fix this overlap and are combined differently in each
project (six projects, five Git hook setups, on 2026-11-09), while baloo grew into one plugin that
does everything, behind a Config of its own.

## Users

- Everyone who works with Claude Code in a project set up for bunderlog's plugins, in one project
  or many, on one machine or several. Each gets the project's Setup (`CLAUDE.md`, `.claude/` with
  its rules and settings, and its Git hooks) and its knowledge (`.about/`) from what it commits,
  keeps their own rules and preferences in their own `~/.claude/`, and sees the projects worked on
  from their machine.
- bunderlog's maintainer, who changes its plugins, and how they work with `hathi`, in
  `claude-plugins`.
- Not for: people without git and a terminal (Cowork), or on Windows.

## Success signal

- A project worked on from this machine that needs attention shows, without opening it, in the
  Status line of a session in any project, for everyone who uses bagheera's line; the visibility
  PRD says what needs attention.
- Everyone working in a project gets the same Setup from the repo.
- What one person's session decides or leaves open in a project reaches the others through
  `.about/`, the project's tracker or its Inbox, once that person accepts, commits and pushes it.

## Scope

- This PRD builds nothing itself: its criteria are met through the PRDs named under Non-goals and
  through changes to the plugins, each with a PRD of its own.
- Required: git, Claude Code, and the `python3` 3.9 or later bagheera and louie run on, which
  macOS's Command Line Tools and most Linux distributions ship (ADR binary). Anything else (mise,
  `hathi`, husky, a CI, a tracker) is the project's own choice.
- Each tool does one job, split by who turns it on and what it is made of:

  | Tool | Its job | Made of | Turned on by |
  | --- | --- | --- | --- |
  | baloo | the project's decisions, requirements and terms are explicit, in one place and in Claude's context; Claude works by shared Guidelines | skills, Guidelines and one SessionStart Hook in `sh`, no Python | the project, for everyone in it |
  | louie | agreed work reaches a checked pull request by its stack's Guidelines; a new product, once set up, starts from a template | Guidelines per stack, templates, workflows, one Hook | the project, for everyone in it |
  | bagheera | the person's sessions keep Secrets out of the context, show which project needs attention, and lose neither a decision nor a lesson; the person's repos get set up | Python, an Output style | each person, once, for every session |
  | `hathi` | no commit that breaks the project's rules enters its history | a Go binary, no Claude | the project's Git hooks and CI |

- The plugins are released together, under one version for the marketplace. No tool calls another's
  code or shares code with it, `hathi` included: they work together only through files whose layout
  a PRD sets (`.about/`, Transcripts, `.hathi.yml`, the Git hooks). Each plugin ships what it
  runs: a helper copied into two plugins is not shared code.
- Workflows are Claude Code's dynamic workflows: scripts a plugin ships that run many agents, which
  a project turns on in its settings.
- Where `python3` is missing, bagheera's and louie's Hooks let every call through, and baloo's
  session start says so once per clone.
- No plugin has a Config of its own: a plugin is on where Claude Code's settings turn it on, and
  then all of it is on; a person turns bagheera's Checks off only by turning bagheera or its Hooks
  off.
- What baloo does today moves: its knowledge skills stay; `verify` and its agent, the stack
  Guidelines and the templates go to louie; the Session review, Retro, Status line, `doctor`,
  Checks in Hooks and `short-replies` go to bagheera; its Config goes, and its Git hooks and commit
  Checks go to `hathi`.
- A project is set up once the commit checked out holds what the PRD setting a project up lists,
  among it: `.claude/settings.json` that adds bunderlog's marketplace and turns on baloo (louie and
  Workflows too, once louie ships), and denies Claude reading Env files and keys; a `CLAUDE.md`
  line that imports the file setting the commit format; and Git hooks that check commits for
  Secrets. Those files come only from setting the project up, a step whose result someone
  commits. A clone counts as set up when its committed `.claude/settings.json` turns baloo on;
  bagheera's `doctor` checks the rest. Setting a project up is bagheera's, since baloo and louie
  are off until it is done.
- "Once per clone": each message is given to a clone once, and again only when it is cloned anew.
- Every kind of fact has one place, where it is read when it matters:

  | Fact | Place | Read |
  | --- | --- | --- |
  | about a person and how to work with them in one project | their Claude's memory of that project | every session there |
  | a person's rules and preferences for all their projects | their `~/.claude/`, written when they ask | every session |
  | a lesson for everyone in any project | baloo's always-on Guideline, or the Guideline on its subject | every session, or when its task comes up |
  | a lesson for everyone on one stack | louie's Guideline for that stack | when a file of the stack is first touched |
  | why a feature or the product exists and what it does, with its decisions about what | `.about/prd/`, or the tracker the project's `CLAUDE.md` names | in the project |
  | how something is built, and why that way | `.about/adr/` | in the project |
  | what a project term means | `.about/glossary.md` | in the project |
  | what is still to decide | `.about/inbox.md` | through `/baloo:inbox` |
  | work agreed to do | the project's tracker, else `.about/issues/` | by the team |
  | an instruction for Claude in the project, naming the ADR or PRD it comes from | `CLAUDE.md`, `.claude/rules/` | at session start, or when a matching file is touched |
  | a decision about one project's own Setup, such as how it runs `hathi` | that project's `.about/adr/` | in the project |
  | a decision about bunderlog's plugins, `hathi` or how they work together | `claude-plugins/.about/`; `hathi`'s own in its repo | when the Harness changes |

  A lesson reaches a Guideline as a change to the plugin, through its Release. A Proposal waits in
  `.about/proposals/`, which the project's `.gitignore` keeps out of git, until someone accepts it
  into its place; the plugins' other working files (logs, their data folders) hold no fact of this
  table, and what is derived from it (an index of the project's decisions and terms) is derived
  again, not kept.

- The layers and who owns each:

  | Layer | What | Who, where | Takes effect |
  | --- | --- | --- | --- |
  | Commits | message format, no Secrets, no AI co-author, linear history, an ADR's Date set when it changes (a `hathi` Check the project turns on in `.hathi.yml`) | `hathi`, run by the project's Git hooks and CI where it installed it; else the project's own Git hooks, which check for Secrets at least; no plugin installs a Git hook | each commit, CI |
  | Claude's commits | the message format Claude writes, no co-author trailer | a line in the project's `CLAUDE.md` that imports the file setting the format (`@.hathi.yml`, which then states the format in full rather than leaning on `hathi`'s defaults, or the project's own); Claude Code's attribution off in `.claude/settings.json` | each commit Claude makes |
  | Knowledge | ADR, PRD, glossary, Inbox, Issues, and an index of them in the context | baloo | each session |
  | Working rules | Guidelines | baloo: its always-on Guideline in the context of every session, another when a task calls for it | each session |
  | Stack Guidelines | a Guideline per stack | louie, when a file of its stack is first touched in a session | when the stack comes up |
  | Delivery | from an agreed Issue to a pull request, checked against what the project agreed | louie's workflows | when someone runs one |
  | Session guards | Secrets kept out of Claude's context, and no mark that lets a Secret through a commit Check (`baloo:allow-secret`, `hathi:allow-secret`, `gitleaks:allow`) added by Claude; Git hooks not skipped by Claude's commands (pointing git at the project's own committed hooks is setting up, not skipping) | Claude Code's own deny rules in the project's `.claude/settings.json` where they can say it; bagheera's Checks in Hooks for the rest | each tool call |
  | Past sessions | what was decided but not written down; where sessions stalled | bagheera's Session review and Retro | at a session's end; when the person asks |
  | Project rules | `CLAUDE.md`, `.claude/rules/` with `paths:`, `settings.json` | Claude Code itself, files in the repo | session start; a rule when its file is touched |
  | Outside systems | where tasks and knowledge live outside `.about/` | a line in `CLAUDE.md` | when a skill writes there |
  | Output style | how Claude replies | the person's own choice in `~/.claude/settings.json`, bagheera's `short-replies` among them | each reply |
  | Personal instructions | language, working style, their own Output style or Status line | each person's `~/.claude/` | each session |
  | Visibility | projects needing attention, sessions waiting for their person, and what to do about each | bagheera's Status line, unless the person set their own, and bagheera's `doctor` (a PRD of its own) | always in view |
  | Harness checks | whether it works: evals, measurements | evals in `claude-plugins`; the measurement's scripts outside it (ADR measurement) | when the Harness changes |

- How the plugins, and their work with `hathi`, change: one change at a time, a PRD first for a
  feature, tried in a pilot project from the checkout (`--plugin-dir`) before its Release, and a
  Release per change.

## Considered options

- A second repo for the Harness (`marketplace`, `harness`) — a second home for its decisions, where
  `claude-plugins` already is the `bunderlog` marketplace, named as Anthropic names theirs.
- Starting again from an empty repo — the history of the decisions would be lost, and moving step
  by step is no worse.
- `hathi`, mise and GitHub required in every project — `webui` had none of them on 2026-11-09.
- A template tool, such as Copier, to bring a Setup into a project — one more tool on every machine,
  for copying a few files a skill can copy.
- One plugin for everything, as baloo was until 2026-11-09 — a Config of its own, its own YAML
  parser and a switch for each part, about 2,500 of its 7,100 lines of Python, only to turn parts
  on and off that Claude Code's own settings turn on and off.
- A plugin per role (`bagheera` for developers, `kaa` for testers, `akela` for product managers) —
  dropped on 2026-10-07: besides the knowledge there was too little to split (ADR plugin).
- Five plugins, the Status line and past sessions each one of their own — they are turned on the
  same way, by each person for every session, so the split would cost two more installs and two
  more copies of the same helpers.
- baloo installing the binaries it recommends, or a manager of our own for them — Git hooks and CI
  run where no plugin does, and mise and the marketplace already install and update.
- The Status line as a binary — in Python it draws in about 80 ms, under Claude Code's 300 ms.
- TypeScript instead of Python — `node` is on the maintainer's machines, not on everyone's, and the
  rewrite of about 4,000 lines would change nothing for those who use the plugins.
- A visibility page or tool of its own — it would wait to be opened, as the Guidelines waited to be
  read (5 of 79, ADR measurement); the Status line is always in view.
- Guidelines that wait for Claude to read them — read 5 times in 79; given by a Hook on the task's
  signal, before the first edit 15 times in 22 (ADR measurement).
- Copies of the stack Guidelines in each repo's `.claude/rules/` — they drift from their source.
- An index of decisions and terms kept in a file of its own, such as `.about/index.md` — a second
  place for every decision; the titles of the ADRs and PRDs already state them.
- Lessons for all projects kept in `claude-plugins` outside a plugin — Claude in another project
  never reads them.
- baloo's own commit Checks where a project has no `hathi` — the same Checks in two places, drifting
  apart.
- A project without `hathi` left with no Secrets check on its commits — a person's commit can leak a
  Secret no session ever saw.
- A commit format written out in `CLAUDE.md` — a second place for `.hathi.yml`'s rules, drifting
  from it. Session start reading `.hathi.yml` — a plugin tied to the format of `hathi`'s config.
- An ADR's Date checked by a Hook on Claude's commits — it misses `git add -A && git commit` in one
  call, `commit -a`, scripts and people's commits.
- Session start turning a clone's Git hooks on itself — it would change git's config, which `hathi`
  declined to do too (its ADR hooks).
- Session start writing the Config, settings or Git hooks into the project, as baloo did until
  2026-11-09 — six projects had five different Git hook setups.
- A plugin's Status line or Output style over a person's own, whether written into the project's
  settings or forced by the plugin (`force-for-plugin`) — they replace what the person chose.
- Workflows kept in each project's `.claude/workflows/` — they drift apart, as `webui`'s already
  has; in baloo — it would need code beyond its one session-start Hook.
- A plugin's version pinned in each repo — a bump in every project at each Release, and a session
  runs the version it started with anyway.

## Non-goals

- Each of these is a PRD of its own: visibility in the Status line and `doctor`; setting a project
  up, the skill that does it included; delivery from an Issue to a pull request, `verify` included;
  stack Guidelines given on a file's first touch; the index of decisions and terms at session start;
  a new project's rails; what a PRD and an ADR each hold, a criterion checked by hand included (the
  knowledge skills `prd`, `adr` and `glossary`); and a simpler Session review.
- Moving existing projects off baloo's Git hooks, its Config, a committed `outputStyle`, and a
  `statusLine` or `outputStyle` baloo wrote into a clone's `.claude/settings.local.json`, and
  choosing what checks a project's commits for Secrets where it has no `hathi`: part of setting a
  project up, recorded in that project's ADR.
- `hathi` taking the ADR Date Check over from baloo: a change to `hathi`'s PRD, which today leaves
  it in baloo, made in its repo.
- Rewriting the ADRs this changes (plugin, binary, config, checks, git-hooks, guidelines, doctor,
  output-styles, status-line, session-review, transcripts, verify, evals, releases; prd and
  about-folder for what a PRD and an ADR each hold) and their glossary entries: each changes with
  the PRD that builds the change, and until then describes baloo as it is.
- Replacing a project's own tools: its husky, CI or tracker stay.
- Moving the existing ADRs' decisions about what into PRDs at once: one file at a time, when it is
  next touched.
- Seeing one machine's projects from another, and bringing a person's `~/.claude/` to another
  machine: theirs.
- Whether bagheera writes its Status line into `~/.claude/settings.json` where none is set, after
  the person's yes, or only says once how to set it, since a plugin can't set `statusLine` itself:
  the visibility PRD settles it.
- How large the Workflows of a set-up project may be (`workflowSizeGuideline`, `small` by default
  on Pro, fewer than 5 agents): the delivery PRD settles it.

## Anti-goals

- A fix adds a required tool where Claude Code, or what the project already has, would do.
- A fact gets a second place, other than an instruction that names where it comes from.
- More than one feature of the plugins, or of their work with `hathi`, is being built at a time,
  from its first commit of code to the Release that ships it; a `fix`, and a PRD such as this one
  that builds nothing itself, aside.
- A plugin changes a file of the Setup that git tracks on its own, not at someone's request.
- One person's own rules, paths or preferences reach another through the project's committed files.
- A tool needs another's code to work, or grows a switch Claude Code's own settings already are.

## Acceptance criteria

- On a machine with only git, Claude Code and `python3` 3.9 or later, `claude plugin marketplace add
  bunderlog/claude-plugins` and `claude plugin install bagheera@bunderlog` are the whole install:
  a session in any folder then has bagheera's Checks in Hooks. Checked by hand on a clean machine.
- A person with that install who clones a project set up for the plugins, opens it and trusts the
  folder has baloo and louie on in the next session, with no command of their own. Checked by hand
  on a clean machine.
- In a project with no `mise.toml`, no `hathi`, no GitHub remote and no `gh`, session start and
  bagheera's `doctor` report no problem that names them (they list a recommendation of `hathi` as
  advice, not as a problem), and no
  Hook exits non-zero for their absence; a skill may still name one that the project's own choice
  needs, such as `gh` for its CI.
- A session start writes only into the plugins' data folders: never a file in the project, tracked
  or not, never git's config, and never `~/.claude/settings.json` without the person's yes.
- In a git repository that isn't set up, bagheera's session start says once per clone that it
  isn't, and how to set it up; bagheera's Checks in Hooks run there all the same.
- In a clone of a project that commits its Git hooks, where they aren't turned on (the layouts that
  count and the command for each: the PRD setting a project up), session start says once per clone
  how to turn them on, and changes nothing itself.
- In a project set up without `.hathi.yml`, session start recommends `hathi` once per clone, with
  how to add it, and changes nothing itself.
- With every other plugin of the marketplace off, each plugin's skills load in a project set up
  for the plugins, and its Hooks let through a call that breaks none of its rules.
- At each Release tag, every plugin's `plugin.json` carries the same version, and the marketplace's
  entries carry none.
- A skill writes each fact only to its kind's place in the table: a term to `.about/glossary.md`, a
  decision about how to `.about/adr/`, a feature's why and what to `.about/prd/` or the named
  tracker, agreed work to the named tracker or `.about/issues/`, a question still open to
  `.about/inbox.md`, with what and how told apart as the knowledge skills' PRD says; none writes a
  fact of these kinds into Claude's memory. Checked by an eval case for each kind of fact each skill
  writes.
- An instruction a skill writes into `CLAUDE.md` or `.claude/rules/` ends with the ADR or PRD it
  comes from, as `(ADR <subject>)` or `(PRD <feature>)`.
- Every `feat` commit under `plugins/` committed from 2026-11-10 names a PRD in its body (`PRD
  <feature>`), and every `fix` the PRD, ADR or Issue it brings the code back to.
- In an eval project with `hathi`, set up for the plugins, the commit message Claude writes passes
  `hathi check commit-msg` (its `conventional-commits` and `no-ai-coauthor` Checks), run on it
  after the case, with one `git commit` call, in two cases: `.hathi.yml` as set up, and with the
  type the case's change needs renamed (such as `feat` to `feature`).
- In `claude-plugins`, `hathi` and `checkmeup`, once set up and with their Git hooks turned on, a
  commit that adds a made-up AWS access key ID (`AKIA` and 16 random characters from A–Z and 2–7,
  not a published example) is refused by the project's Git hooks, whether a person or Claude makes
  it. Checked by hand.
- In a project set up for the plugins, Claude's `cat .env`, `head .env.local` and `cat
  ~/.aws/credentials` are refused by the project's deny rules, bagheera on or off. With bagheera
  on, so are `env`, `printenv`, `set`, an `echo` of a variable whose name says key, token, secret
  or password, an Allow mark Claude adds, and `git commit --no-verify`.
- In `claude-plugins`, `hathi` and `checkmeup`, once set up, bagheera's `doctor` reports no problem
  with what the PRD setting a project up says a project holds. Checked by hand.
- A project's committed Setup files (`CLAUDE.md`, `.claude/`, its Git hooks) hold no absolute path
  into a home folder or a plugin's data folder (a deny rule starting `~/` is none), and its
  committed settings set no `statusLine` and no `outputStyle`.
- Two people who open the same commit of a project with the same plugin version get the same
  baloo and louie skills, workflows, Guidelines, `.claude/rules/` and deny rules from it, as
  bagheera's `doctor` lists them for each (checked by hand in two clones), except
  the rules for their shell and what depends on whether their clone's Git hooks are on or `python3`
  is missing, and unless their own settings turn a plugin or its Hooks off.
- A person who sets their own Output style or Status line in `~/.claude/settings.json` gets it in
  every project from their next session on; no plugin's Output style sets `force-for-plugin`, and
  where baloo had set its own in a clone's `.claude/settings.local.json`, bagheera's `doctor` names
  that line for the person to remove.
- The Release that takes the commit Checks out of baloo ships only once `hathi` has the ADR Date
  Check and each project worked on from the maintainer's machine since 2026-10-01, as Claude Code's
  Transcripts list them, is set up for the plugins or named, with why not, in Issue
  commit-checks-to-hathi; from it on, a Git hook baloo wrote lets each commit through, saying that
  baloo no longer checks it and how to remove the hook, and still lets it through once baloo has no
  Python.
