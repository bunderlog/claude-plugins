# Each person's own deny rules keep Secrets' files out of Claude's context in every folder

## Problem

A set-up project denies reading Env files and private keys in its committed
`.claude/settings.json` (PRD project-setup), but those rules hold only in that project: in the home
folder, in a repo not set up (12 of the 22 in `~/Projects` on 2026-11-11), and outside any repo,
only bagheera's `no-secrets-in-context` stands between Claude and `~/.aws/credentials`. That Check
reads tool calls and shell commands, so it can't see what reaches Claude another way: a Glob's
results, a file `@`-mentioned in a prompt, an IDE's open file, a symlink to a Secret's file; and
where `python3` is missing or the plugin fails, no Check runs at all (ADR binary). Claude Code's own
`Read` deny rules cover all of these, best effort, and hold in every folder when they sit in the
person's `~/.claude/settings.json` anchored with `//` or `~/`.

## Users

- Each person with bagheera installed: one yes, once, and the rules hold in every session.
- Not for: a team that wants the rules for everyone; that is a project's committed settings (PRD
  project-setup), or the machine's managed settings.

## Success signal

On the maintainer's machine, `~/.claude/settings.json` holds the rules, and a session in the home
folder that asks to `@`-mention `~/.aws/credentials`, or to Glob for `**/.env`, gets neither file's
contents, checked by hand once after the Release.

## Scope

- bagheera's rules, each a `Read` deny rule for every folder: `//**/.env`, `//**/.env.local`,
  `//**/.env.*.local`, `//**/.env.development`, `//**/.env.production`, `//**/.env.staging`,
  `//**/.env.test`, `//**/.envrc`, `//**/*.pem`, `//**/*.key`, `//**/id_rsa`, `//**/id_ed25519`,
  `~/.ssh/id_*`, `~/.aws/credentials`, `~/.netrc`, `~/.docker/config.json` and
  `~/.config/gh/hosts.yml`: the project's list, anchored for every folder, and the files
  `no-secrets-in-context` knows to hold Secrets.
- The person's own settings are Claude Code's user settings file, `settings.json` in
  `CLAUDE_CONFIG_DIR` or else `~/.claude/`; a rule counts as there when that file's or the managed
  settings' `permissions.deny` holds its exact text.
- Session start, where the person's own settings lack any of them, has Claude offer to add the
  missing ones to that file's `permissions.deny`, keeping its other settings, and add them only on
  a yes, as it offers the Output style and the Status line (ADR status-line), in a line of its own:
  once per machine, the mark kept in bagheera's data folder, so a person who says no hears it once,
  and a rule a later Release adds is named by `doctor`, not offered again. It offers in any folder,
  in a repo or not, and not in a headless session. Where the file isn't JSON, or its
  `permissions.deny` isn't a list, it offers nothing.
- `doctor`, in any folder, names as a problem the rules the person's own settings lack: the file,
  and the missing rules as the JSON list to add to its `permissions.deny`; a file it can't read is
  a problem too.
- `no-secrets-in-context` stays as it is: the rules are a second layer, not its replacement.

## Non-goals

- Turning on Claude Code's sandbox, which enforces the paths for every process: a person's choice,
  with costs of its own.
- Writing the rules into managed settings, or into a project's committed ones beyond PRD
  project-setup's list.
- An Env file named otherwise, such as `.env.prod`: the Check keeps guarding it; a rule for
  `.env.*` would deny `.env.example` too, and a `!` carve-out can't reach a `//` rule.

## Anti-goals

- bagheera writes into `~/.claude/settings.json` without the person's yes.
- A Check that guarded a session stops guarding it (PRD bagheera).
- A template, `.env.example` or `.env.sample`, becomes unreadable.

## Acceptance criteria

- With the person's own settings holding none of the rules, session start offers to add all of
  them, its line naming the file and each rule; the next session start, in another repo too,
  doesn't offer again; a headless session start doesn't, and doesn't use the offer up; outside a
  repo it offers as in one.
- With the file holding some of the rules, the offer names only the missing ones; with all of
  them, there is no offer.
- Session start writes nothing into `~/.claude/settings.json`.
- `doctor` with two of the rules missing from the person's own settings names the file and those
  two, and exits 1; with all present, it names none of them.
- No rule matches `.env.example` or `.env.sample`.
- `no-secrets-in-context`'s tests pass unchanged.
- With the rules in `~/.claude/settings.json`, a session in the home folder gives no contents for
  an `@`-mention of `~/.aws/credentials`, and one in a repo reads `.env.example`. Checked by hand.
