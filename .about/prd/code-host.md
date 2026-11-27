# louie reaches the Code host through an MCP server of its own, on GitHub and Bitbucket Cloud

## Problem

A project whose Code host is Bitbucket Cloud gets `/louie:implement` only up to the push, and no
`/louie:merge` at all: every step that touches a pull request calls GitHub's client. So the
person steers each pull request by hand. In `webui`, from 2026-10-28 to 2026-11-25, "code review
PR … merge … move the ticket to RFT" was typed 27 times, each run calling Bitbucket's API by hand
with a token read from a settings file.

On GitHub too, the rules that keep a merge safe (merge only the commit the Verification passed,
only onto the base the rebase used, only once CI passed) are text in the implementer's
instructions, which nothing tests (ADR merge).

## Users

- A developer in a project with louie and Workflows on, on GitHub or on Bitbucket Cloud, who wants
  `/louie:implement` and `/louie:merge` to work the same on both.
- Not for: Bitbucket Data Center or Server, GitLab, or any other Code host.

## Success signal

- In the month after the GitHub part's Release, every `/louie:merge` run in this repo ends as it
  would have before, and the default branch's CI passes after every merge it makes.
- In the month after the Bitbucket Cloud part's, `webui`'s pull requests reach its default branch
  through `/louie:implement` and `/louie:merge` with no pull-request step typed by hand, and the
  token's value appears in none of those sessions' Transcripts.

## Scope

- louie's MCP server, `code-host`, in `plugins/louie/scripts/` and declared in louie's manifest
  (ADR code-host), with a tool for each thing a stage asks of the Code host: `repo` (its default
  branch, that branch's tip, the merge methods it allows), `pr_open` (a draft when asked),
  `pr_read`, `pr_checks` and `pr_merge`. Each takes the folder, a checkout or a worktree, whose
  `origin` it works on, and answers in JSON. Every stage of `implement` and `merge` that asks the
  Code host calls these tools in place of the Code host's own client, and the implementer's
  `tools:` names them.
- It tells the Code host from the URL of the remote `origin`: a host of `bitbucket.org` is
  Bitbucket Cloud; any other is GitHub, as now, so a GitHub Enterprise or SSH-alias remote runs as
  it does today. The project configures nothing for it.
- On GitHub it calls `gh`, signed in by the person as now; louie holds no GitHub token.
- On Bitbucket Cloud it calls Bitbucket's API with the token in the environment variable
  `BITBUCKET_TOKEN`: with `BITBUCKET_EMAIL` set too, as an API token and that account's email
  (Basic auth); without it, as a repository or workspace access token (Bearer). The project
  configures nothing for it. The token is never shown: not in a tool's answer, a file or a pull
  request the run writes, even when the API repeats it in an error. With the token not set, every
  tool returns `no-token` and calls no API. Each prepare calls `repo` first, before a worktree or
  a branch is made, so an `implement` run ends `blocked:prepare`
  naming `no-token`, as its other prepare stops do, and that pull request of a `merge` run ends
  `blocked:no-token`.
  - The rules a merge rests on move from the implementer's text into the server's code, the same
  on both
  hosts:
  - it merges only when the pull request's head is the commit it is given and the default
    branch's tip, read through the Code host's client, is the base it is given; on GitHub the
    head is checked by the merge itself, on Bitbucket Cloud read again right before the merge,
    the seconds between accepted as ADR merge accepts them for the base. Else it returns
    `head-moved` or `base-moved` and merges nothing; the merge stage reports `head-moved` as a
    refusal, so the run ends `blocked:merge` naming it, as a moved head does on GitHub now;
  - it reads checks as failed when one failed (a failure, an error, a stopped or cancelled one,
    with its name and link), else running while one runs or a run for the head is queued or in
    progress (a GitHub Actions run, a Bitbucket Pipelines pipeline), else passed (each a success,
    a skipped or a neutral one), else none; how long to wait stays the ci stage's, as PRD merge
    has it;
  - it deletes no branch, opening or merging.
- The merge method is named in the Code host's own terms, in the places PRD merge reads it from.
- `/louie:merge` takes a Bitbucket pull request's URL (`…/pull-requests/42`) as its number, as it
  takes a GitHub one's (`…/pull/42`).
- A draft is the Code host's own; `merge`'s prepare stops on one `blocked:draft` on both.
- Two parts, each in a Release of its own, GitHub's first:
  - GitHub: the server for GitHub, with `implement` and `merge` calling it; nothing else changes;
  - Bitbucket Cloud: the server for Bitbucket Cloud.
- With the GitHub part, ADR merge says the merge's rules are in the server's code, whose tools the
  implementer is told to call; as now, nothing stops a stage running another command. With the
  Bitbucket Cloud part, that on Bitbucket Cloud the head is read again right before the merge. The
  README names, for Bitbucket Cloud, the two variables and the token's permissions; and, for both
  hosts, the tools to allow for a run with no permission prompt.

## Non-goals

- `/louie:verify` given a Bitbucket pull request by its number: given its branch, it works today.
- A Ticket kept in GitHub's issues, which the planner reads with `gh issue view` as now.
- Moving a Ticket in the tracker (to RFT), or closing it: the person's, as in PRD implement.
- Creating the token, or the repo's branch restrictions and merge methods: the person's or their
  admin's.
- Reviewing or commenting on a pull request on the Code host.

## Anti-goals

- The token's value in the session's context, a Transcript, a commit or a pull request.
- A merge the rules above refuse, on either host.
- On GitHub, a run that ends otherwise than it would have before the server.

## Acceptance criteria

GitHub:
- Started as louie's manifest declares it, the server answers MCP's `initialize` over stdio and
  lists the five tools with their parameters, and a `tools/call` of `repo` returns its JSON.
- With `gh` stubbed, `pr_merge` passes the head it is given to `gh pr merge` as
  `--match-head-commit`, never `--delete-branch`; returns `head-moved` when `gh` refuses that
  head; and with the default branch's tip, as `gh` reports it, other than the base it is given,
  returns `base-moved` and calls no merge.
- With `gh` stubbed, `pr_checks` returns passed for a passed and a skipped check, failed
  naming the failing check and its link (also while another runs), running while one runs or a
  run for the head is queued with no check shown, and none for none.
- `implementer.md`, `implement.js` and `merge.js` name no `gh pr`, `gh run` or `gh repo` command:
  a test reads them.
- With their agents stubbed, `implement`'s and `merge`'s Workflow tests pass unchanged.
- In this repo, `/louie:implement` on a Ticket opens its pull request, and `/louie:merge` merges it
  after CI, as before. Checked by hand at its part's Release.

Bitbucket Cloud:
- The server tells Bitbucket Cloud from `git@bitbucket.org:ws/repo.git` and
  `https://bitbucket.org/ws/repo`, and GitHub from `github.com`, a GitHub Enterprise host and an
  SSH alias.
- With Bitbucket's API stubbed, the server sends the token as Basic auth with `BITBUCKET_EMAIL`
  set and as Bearer without it; opens a draft when asked and never asks to close the
  source branch; `pr_merge` merges only when the head it reads right before is the one it is
  given, else
  returns `head-moved` and merges nothing; reads a stopped or failed build as failed, and a
  pending pipeline with no build shown as running; with the token's variable not set, returns
  `no-token` from every tool and calls no API; and writes the token's value in no output, also
  when the API's error repeats it.
- With its agents stubbed, an `implement` run whose prepare stops naming `no-token` ends
  `blocked:prepare` naming it and runs no later stage; a `merge` run on two pull requests stopping
  so returns each `blocked:no-token`, runs no rebase stage, and ends `blocked:none`.
- With its agents stubbed, `/louie:merge` given a Bitbucket pull request's URL and its number runs
  it once.
- In `webui`, whose `AGENTS.md` names the merge method, `/louie:implement` on a small
  Ticket with criteria opens a pull request whose title is the Ticket's and whose body names each
  criterion with its verdict; `/louie:merge` merges it by that method once its build passed, and
  on a pull request whose build fails ends `blocked:ci` naming the build, merging nothing. Checked
  by hand at its part's Release.
- Over those runs, the token's value is found in none of the Transcripts (`grep -rF` for it under
  all of `~/.claude/projects/`, the worktrees' folders included). Checked by hand at its part's
  Release.

## Open questions

- Settled 2026-11-27: one MCP server of louie's for both hosts (ADR code-host), GitHub's through
  `gh`, in two parts, GitHub's first; the host told from `origin`, nothing configured; the token
  from `BITBUCKET_TOKEN`, Basic auth when `BITBUCKET_EMAIL` is set, Bearer when not, never shown;
  the head read again before a Bitbucket merge, the race accepted; drafts the host's own; checked
  end to end in `webui`, on a small Ticket.
- Which merge methods Bitbucket Cloud's API offers, and which `webui` allows. Settled by the API's
  reference and `webui`'s settings, at the plan.
- Whether a Workflow's stage, an agent whose `tools:` names a plugin's MCP tools, can call them.
  Settled first at the plan, by a stage that calls `repo`; if it can't, ADR code-host is revisited
  before anything is built.
