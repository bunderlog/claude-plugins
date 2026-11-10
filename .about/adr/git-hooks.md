# The plugin writes no Git hook; a project's own run `hathi`, and an old one of the plugin's passes

Date: 2026-11-11

No plugin's Hook writes a Git hook, and none checks a commit: a project set up for the plugins
commits its own Git hooks, which run `hathi` (PRD project-setup), and its CI runs the same `hathi`.
Only bagheera's setup skill, which the person runs, writes them into the working tree, for the
person to commit (PRD setup). Session
start leaves `.git/hooks` and husky's files as they are, says nothing of Git hooks, and neither
turns off Claude Code's commit attribution nor tells Claude a commit format: the project's
committed settings and `CLAUDE.md`, which imports `.hathi.yml`, do (PRD harness).

A Git hook an earlier Release wrote, marked `# managed by baloo`, still runs `python3 -E -s
<link>/scripts/run.py git-hook <hook>` through the link in the plugin's data folder (ADR binary);
the plugin now lets the commit or push through, saying on stderr that it no longer checks commits
and how to remove the hook. Where the link or `python3` is gone, the hook already passes and says
so. The plugin never removes the hook itself: setting the project up does, or the person.

`git-hooks` and `git-hook-commands` in a Config are removed settings: the Config works as without
them, and only `doctor` names them for the user to delete (ADR config).

## Considered options

- The plugin writing `pre-commit`, `commit-msg` and `pre-push` at session start, each running its
  Checks the Config turned on and the project's command under `git-hook-commands`, into
  `.git/hooks` or, with husky 9, into the git folder's `baloo-hooks/` with a line in husky's
  (until 2026-11-09) — untracked, so a clone ran none until its first session and every clone
  froze at its plugin version, six projects had five setups, and the Checks lived in two places
  once `hathi` had them.
- Removing the Git hooks an earlier Release wrote at session start — a session start that changes
  files in the project, which PRD harness rules out; the hook's own message reaches whoever
  commits.
- Failing a commit through an old Git hook — every commit in a clone not yet set up would stop for
  a hook nobody there wrote.

## Consequences

- A clone not set up has its commits checked by nobody locally until it is, or by `hathi` in CI.
- The link in the data folder stays, for the Status line and for the old Git hooks to pass through.
- Revisit when no clone worked on still has a Git hook of the plugin's: the `git-hook` command and
  its message can go.
