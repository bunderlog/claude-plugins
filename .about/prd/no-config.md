# baloo works without a Config of its own: all of it is on where Claude Code turns it on

## Problem

A project turns baloo's parts on and off in `.claude/baloo.yml`, a file baloo creates at a clone's
first session, with its own YAML parser and about 1,300 lines that only read it and write Claude
Code's settings from it; a teammate's clone gets a Config before anyone decides on it, and what is
on differs from project to project for no reason anyone recorded (PRD harness: no Config, Claude
Code's settings are the only switch).

## Users

- Everyone in a project with baloo on: they get all of it, the same in every project.
- Each person: their Output style and Status line are theirs, in `~/.claude/settings.json`.
- Not for: a project that wants one of baloo's parts off; it turns baloo off.

## Success signal

No project worked on from this machine has a `.claude/baloo.yml`, and session start writes no file
in a project.

## Scope

- What each key of today's Config becomes:

  | Key | Becomes | Release |
  | --- | --- | --- |
  | `claude-hooks` | each Check in Hooks always on | 1 |
  | `guidelines` | every Guideline on, as below | 1 |
  | `output-style` | the person's own `outputStyle`; session start writes none | 2 |
  | `status-line` and its bars and thresholds | the person's own `statusLine`; the line draws its default bars (context, 5h, 7d, cache) at its default thresholds | 2 |
  | `session-review` | the Session review runs in every project with baloo on | 3 |
  | `format-on-edit` | gone: a project adds its own `PostToolUse` Hook in its `.claude/settings.json` (PRD project-setup names how) | 3 |
  | the file itself | read by nobody and created by nobody; `doctor` names it for the person to remove | 4 |

  From the Release named, the key does nothing, and `doctor` names it as a removed setting.
- Guidelines without a switch: a Hook gives each by its task's signal as today, whatever the
  repo's manifests (ADR guidelines); session start's index names the ones no Hook gives, each
  where it fits the repo as a new Config's defaults do today: `principles`, `design`, `debugging`
  and `writing-for-agents` always, `ci` where the root holds a CI's config, `dependencies` where a
  package manager's manifest is, and `go`, `typescript`, `vue` and `tailwind` where a manifest
  names their stack, found by today's walk of the repo, once per session start; outside a repo,
  none, as today.
- Where no settings file Claude Code reads (the person's, the project's or the clone's local)
  sets an `outputStyle`, or a `statusLine`, the first session start in a clone tells Claude, to
  tell the person, how to set each that is unset in `~/.claude/settings.json`: `"outputStyle":
  "baloo:short-replies"`, and a `statusLine` whose command runs `scripts/run.py status-line`
  through the link in baloo's data folder, which stays the same from one version to the next
  (ADR binary). A headless session says nothing of them and leaves the telling for the next.
- `doctor` names, for the person to remove, a `statusLine` in a clone's
  `.claude/settings.local.json` whose command ends `# managed by baloo`, and an `outputStyle` of
  `baloo:short-replies` there.
- Releases 3 and 4 ship as one, since after 3 the Config would hold no setting at all. Each Release
  rewrites the ADRs and glossary entries it changes: 1 ADR checks and guidelines and the entries
  Check and Guideline; 2 ADR output-styles and status-line and the entries Output style and Status
  line; 3 ADR session-review and format-on-edit and the entries Session review and Format on edit,
  moved to Retired terms; 4 ADR config and the entry Config, moved to Retired terms.

## Non-goals

- Moving these parts to bagheera or louie: Issue split-bagheera-louie.
- A simpler Session review: a PRD of its own before it moves.
- Writing the person's `~/.claude/settings.json`: this binds baloo until bagheera ships, and the
  visibility PRD may replace it, with the person's yes.
- New Hook signals for `go` or `tailwind`: louie's stack Guidelines.
- Removing `.claude/baloo.yml` from the projects: setting each project up does, once Release 4 is
  out.

## Anti-goals

- A part of baloo that a project can turn off only by editing a file baloo owns.
- Session start writing into a project, tracked or not.

## Acceptance criteria

- From Release 1, in a repo whose `.claude/baloo.yml` turns `no-secrets-in-context` and
  `no-git-hook-bypass` off, Claude's `cat .env` and `git commit --no-verify` are still refused.
  A new test in tests/test_cli.py.
- From Release 1, in a repo with `go.mod` whose Config turns `go` off, session start's index names
  the `go` Guideline; in a repo without one, it doesn't; and a `.ts` file read in a repo with no
  TypeScript dependency still gives the `typescript` Guideline once in the session.
- From Release 2, where no settings file sets `outputStyle` or `statusLine`, the first session
  start in a clone tells how to set both in `~/.claude/settings.json`, and the next says nothing
  of them; where only one is set, it tells of the other; where both are, it says nothing of
  them; a headless session start says nothing and the next interactive one still tells.
- From Release 2, a session start writes no `outputStyle` and no `statusLine` into any file; with
  a Config holding a `status-line` layout, the Status line prints what it prints with none.
- From Release 3, in a repo whose Config turns `session-review` off, a session's end still starts a
  Session review; a `format-on-edit` key runs nothing.
- From Release 4, in a fresh repo, no file under the repo's folder, `.git/` included, is created or
  changed by a session start; `config.py` and `yaml.py` are gone, and the tests pass on Python 3.9.
- From the Release that drops each key, `doctor` in a repo whose Config has it names it as a
  removed setting; from Release 2, it names a `statusLine` or `outputStyle` baloo wrote into
  `.claude/settings.local.json`; from Release 4, it names `.claude/baloo.yml`.
