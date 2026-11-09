# Commits are checked by `hathi`, and baloo's Git hooks and commit Checks go

2026-11-09

## Symptom

Phase 2 of the move to three plugins (ADR plugin): each project's commits are checked by `hathi`,
or its own Git hooks, from hooks it commits; baloo writes no Git hook and has no commit Check.
Now, because the other phases build on it: nothing else in the move can ship while baloo still
writes Git hooks at session start.

## Evidence

- Six projects had five different Git hook setups on 2026-11-09 (PRD harness, Problem).
- This repo runs `hathi` 1.1.0 through baloo's Git hooks, by `git-hook-commands` in
  `.claude/baloo.yml`; `.git/hooks/pre-commit` is baloo's.
- ADR git-hooks and ADR checks describe the Git hooks and commit Checks baloo has today; `hathi`'s
  PRD leaves the ADR Date Check in baloo.

## Acceptance criteria

- The PRD setting a project up exists and has no Status line. Done: PRD project-setup.
- `claude-plugins`, `hathi` and `checkmeup` are set up by it, by hand: Git hooks that run `hathi`
  committed, `CLAUDE.md` importing `@.hathi.yml`, no committed `outputStyle`.
- `hathi` has the ADR Date Check, in a Release of its own. Done: `hathi` 1.2.0.
- PRD harness: "The Release that takes the commit Checks out of baloo ships only once …" holds.
- PRD harness: "In `claude-plugins`, `hathi` and `checkmeup`, once set up and with their Git hooks
  turned on, a commit that adds a made-up AWS access key ID … is refused" holds.

## Comments

### 2026-11-09 · order

The PRD setting a project up first, then `hathi`'s ADR Date Check, since baloo leaves a committed
hooks folder alone and its own Check stops running there, then the projects by hand, then baloo's
Release. The other projects worked on from this machine since 2026-10-01
(Claude Code's Transcripts list them) are set up before that Release too.

### 2026-11-09 · fix option

The Git hook baloo wrote already lets a commit through when the plugin's code is missing (it exits
0 with a message), so the Release only has to make its message say that baloo no longer checks
commits and how to remove the hook.

### 2026-11-09 · which projects

Set up on this machine: `claude-plugins`, `hathi`, `chainofsale`, `checkmeup`, `mongo-leader` and
`sagsuget.co.il`. Not set up, by the owner's call: `webui`, a work project that keeps its own Setup
and stays on baloo 0.34.0; `vidcrunch-cto`, which has no remote and keeps `.claude/` out of git.
The owner's projects on the work computer are set up from there.
