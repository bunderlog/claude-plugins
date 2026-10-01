# bunderlog/claude-plugins

The `bunderlog` marketplace of Claude Code plugins. It holds one plugin, `baloo`, described in
its [plugin.json](plugins/baloo/.claude-plugin/plugin.json).

```sh
claude plugin marketplace add bunderlog/claude-plugins
claude plugin install baloo@bunderlog
```

Why things are the way they are is in [.about/adr/](.about/adr/).

## Git hooks

At session start the plugin writes the Git hooks `pre-commit`, `commit-msg` and `pre-push`
where `.claude/baloo.yml` turns on one of their Checks under `git-hooks`, and takes its own out
where it turns them all off. A Git hook already there that the plugin didn't write is left alone,
and session start names the Checks it keeps from running. With husky 9, the plugin's Git hooks go
into `.git/baloo-hooks/`, and a line first in `.husky/<hook>` runs each: commit that line.

## Stop check

With `stop-check: <command>` in `.claude/baloo.yml`, such as `stop-check: mise run check`, the
plugin runs the command in the repo's root when Claude ends a turn that changed the working tree,
and hands a failure back to Claude to fix before it stops, once a turn.

## Format on edit

With `format-on-edit: <command>` in `.claude/baloo.yml`, such as `format-on-edit: npx prettier
--write`, the plugin runs the command in the repo's root with the path of each file Claude edits,
and says nothing of how it went; the Stop check reports what still fails at the turn's end.

## CI

The Checks that Git hooks run can run in a project's CI too, for commits made where the Git
hooks didn't: without the plugin, or in GitHub's web editor. Download the binary of a pinned
Release, check it against the Release's `SHA256SUMS`, and give each Check the input its Git hook
would, with `$BASE` the commit the checked commits start from:

```sh
set -e
version=0.9.0
file=baloo_${version}_linux_amd64
dir=$(mktemp -d)
for f in "$file" SHA256SUMS; do
  curl -fsSL -o "$dir/$f" "https://github.com/bunderlog/claude-plugins/releases/download/v$version/$f"
done
(cd "$dir" && grep " $file\$" SHA256SUMS | sha256sum -c -)
baloo=$dir/$file
chmod +x "$baloo"
for sha in $(git rev-list "$BASE"..HEAD); do
  git log -1 --format=%B "$sha" > "$dir/msg"
  "$baloo" check conventional-commits "$dir/msg"
  "$baloo" check no-ai-coauthor "$dir/msg"
done
echo "refs/heads/ci $(git rev-parse HEAD) refs/heads/base $BASE" | "$baloo" check linear-history
git reset -q --soft "$BASE" # the checked commits' changes, staged
"$baloo" check no-secrets-in-commits
```

- Check out the head with its full history, not a merge commit. In GitHub Actions that is
  `fetch-depth: 0`, and on a pull request `ref: ${{ github.event.pull_request.head.sha }}` with
  `BASE=$(git merge-base <the base's sha> HEAD)`; on a push, `BASE` is `github.event.before`.
- Each Check takes its settings from the repo's `.claude/baloo.yml`, as in its Git hook, and one
  the Config turns off passes.
- `no-stale-adr-date` is left out: it compares an ADR's Date with today, so a change checked on a
  later day than it was made would fail.
- How a Check takes its input follows the Git hooks, not a promised interface; the pinned version
  keeps a later Release from breaking CI.

## Development

This repo uses its own plugin: `.claude/settings.json` installs `baloo` from GitHub, so a session
here runs its last Release. To try an edit to a skill, Guideline or Hook before a Release, start a
session with `claude --plugin-dir plugins/baloo`; the binary is still the last Release's. Its
source is in `src/baloo/`, and `mise run check` checks its formatting, vets it and tests it. To
make a Release, run `mise run release` and push it with `git push --follow-tags`.
