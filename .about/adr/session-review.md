# A Session review proposes, after each session, what it settled but nobody wrote down

Date: 2026-10-09

A session often settles a term or a decision that nobody records, and it is lost when the session
closes. Where the Config has `session-review: true`, the `SessionEnd` Hook runs the binary's
`session-end`, which starts a Session review and returns at once: a separate headless `claude -p`,
detached so that Claude Code's exit never waits for it, run at the repo's root with the
`glossary` and `adr` skills. It loads the plugin from its own folder too, since the review's
session may not have it otherwise, as where the ended session had it from `--plugin-dir`. A new
Config turns it on; without the key it is off, since it didn't exist before the key (ADR config).

The review reads only the user's and Claude's text, masked as a Retro's is (ADR transcripts),
and at most the last 200,000 characters of it: no tool call or result. It skips a session shorter
than 2,000 characters, which can't have settled much, and a headless one, its own or another
tool's, and a review never starts another. Only what the conversation clearly agreed, and only
about the repo it runs in, is proposed. Anything contested or left open, and a bug or a problem
the session found but didn't fix, is an Inbox item to add, and an item the conversation settled
one to delete (ADR inbox).

It edits nothing in `.about/` itself: it writes Proposals, each a change to the Inbox, the
glossary, an ADR or a PRD that the user accepts, rejects or defers. Each review has an id, when it
started and the first eight characters of the ended session's id, such as
`20261007T174211Z-acf806f4`, and writes its Proposals to `.about/proposals/<id>.md`: a
`## <P1> · <target> · <kind> · <path> · <title>` heading each, the target `inbox`, `glossary`,
`adr` or `prd`, the kind `add`, `edit` or `delete`, a line of why, and the ready edit, the text it
changes under `Before:` and the text it puts there under `After:`, each in a `~~~` fence, which the
binary also reads as a ``` one, as a reviewer sometimes writes it anyway. Its tools
are reading and writing that folder only; anything not allowed is denied rather than asked, and it
never commits. The folder goes into the repo's `info/exclude`, not into git: a Proposal is a
retelling of the conversation the user hasn't agreed to yet, and a commit of "everything" would
take it in unread.

Session start shows Claude the Proposals still waiting, a line each, and tells it to show the user
the list and ask, for each, accept, reject or defer, reading the file for the full edit; it says so
too where a review is still running, and the first prompt after that review ends shows its Proposals
then. Each session is shown a Proposal once. An accepted one is applied through its skill,
`glossary`, `adr` or `prd`, or, for the Inbox, by its edit as written, since the `inbox` skill isn't
for adding one item. Its After stays as the review proposed it: where the applied text differs,
Claude adds an `Applied:` block of that text to the Proposal and logs it `accepted-edited`, which
counts as accepted, and the checks below read Applied where it is there. Claude logs each answer
with the binary's `review-decision`, through the Loader. A Proposal waits until it is accepted or
rejected: deferred, it comes back in the next session, at most twice; then only accept or reject are
offered. When the Before of an edit or a delete is no longer in its file, the Proposal is stale: it
can be accepted only once fixed by hand, and rejecting it is recommended. A Proposal whose log and
file disagree, accepted but not in its file, or in its file with no decision logged, is shown as a
mismatch, and `doctor` counts it. Once each of its Proposals is accepted or rejected and in its file
as decided, the file moves out of the repo into the plugin's data folder, the repo's `decided/`
there, and is kept for good: what a review proposed, beside what was applied, is what a later
measurement judges its quality by.

Nothing is shown in a headless session, such as a project's own `claude -p` in a Git hook: Claude
Code sets `CLAUDE_CODE_ENTRYPOINT` to `sdk-cli` there, `cli` with the user, which both a
SessionStart and a UserPromptSubmit Hook get. Showing consumes nothing, so a Proposal shown where
nobody answers still waits. No headless session of any kind gets a review either, `claude -p`'s
or the Agent SDK's, whose entrypoints all start `sdk-`: nobody there agreed anything with the user,
and a Git hook's reviewer of commits would leave Proposals after every commit.

The log of decisions is `session-review.log` in the plugin's data folder: a line a decision, its
fields split by tabs: when, in UTC; the repo, its origin's URL without a user or password, or its
root where it has none, so logs from two machines join; the review's id, the Proposal's id, its
target, its kind; and `accepted`, `accepted-edited`, `rejected` or `deferred`. Every line parses the
same way, so the share of Proposals accepted is counted without guessing. Each review's reply,
process id and errors are files of its own id in the repo's folder beside the log, deleted a week
after it ended; `decided/` is in that folder too.

Its session changes nothing else either: there session start creates no Config, picks no Output
style, sets no Status line and writes no Git hook, and no Format on edit runs. A review starts as
the user may be opening their next session, whose session start writes the same settings files.
The Checks a Hook runs still run there, so a tool call of the review's can't show it a Secret;
session start still names the Guidelines. It runs with the user's default model.

## Considered options

- Editing `.about/` itself, its reply shown once at the next session start (until 2026-10-07) —
  of its 80 changes in other repos, 64 were Inbox items; the next review overwrote 21 of its
  replies, which were one file per repo, and a project's headless reviewer of commits took 9, its
  session start reading and deleting the reply; of 20 reviews whose reply the user never saw, the
  changes of 19 were committed anyway (ADR measurement).
- The Proposals committed — the team would see them and a second machine too, but a commit of
  everything would take them in unread, as it took the edits, the repo may be public, and a
  decision logged on one machine would leave the Proposal waiting on the other.
- The Proposals in the plugin's data folder — out of git for sure, but out of the user's sight in
  their editor too.
- A skill to go through the Proposals — its description would be in every session of every
  project; the steps are a few lines at session start, only where a Proposal waits.
- Deferring without a limit — a Proposal nobody decides comes back in every session.
- Rewriting After to the text applied — the log would no longer tell a Proposal accepted as it
  came from one accepted only after a change, and the review's own text, what its quality is
  judged by, would be lost.
- Deleting a decided file — git keeps what was applied, but nothing keeps what was proposed.
- An `expired` decision after a time — a fourth value in the log for what the user never decided.
- Telling a headless session by its Transcript's entrypoint — the Transcript may not be written
  yet at session start, where the environment already says it.
- Only the glossary and the ADRs (until 2026-10-01) — a bug the session found and didn't fix was
  lost with it.
- Dropping it, since most reviews change nothing — the few that do record what would otherwise
  be lost, and what they recorded came up in a later session in 58% of cases.
- Session start as in any other session but for the Git hooks (until 2026-10-01) — nothing
  needed its writes there, and they could race those of the user's next session.
- The Checks a Hook runs off in its session too, so nothing of the plugin runs there — a Read of
  an Env file by the review would go unchecked.
- Off in a new Config too — no tokens without asking, but no review until someone knows to ask.
- Handing over the conversation unmasked — a Secret the user pasted, or Claude repeated, would
  reach one more session and Transcript.
- A cheaper model, pinned — less cost per session, but a subtle decision is more likely missed or
  recorded badly.
- A key for the model — one more setting, for a choice nobody has asked to make.
- Its state in the system's temporary folder under predictable names — shared with every other
  user and process on the machine.

## Consequences

- Every session with a new Config costs a headless run when it ends, most of them proposing
  nothing.
- Nothing reaches `.about/` without the user's answer, at the cost of a question per Proposal.
- A Proposal deferred on one machine waits only there; what was accepted reaches the other
  through git.
- A text match decides stale and mismatch: an accepted Proposal whose skill reworded it is a
  mismatch until its Applied is added.
- The decided files grow in the plugin's data folder with every review, and are lost with it.
- A decision the conversation masked (a long id) can't be proposed exactly.
- Revisit when a review proposes something wrong or about another repo, when its cost shows, or
  when the share accepted stays low.
