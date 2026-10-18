# A Session review proposes, after each session, what it settled but nobody wrote down

Date: 2026-10-18

A session often settles a term or a decision that nobody records, and it is lost when the session
closes. Where the Config has `session-review: true`, the `SessionEnd` Hook runs the plugin's
`session-end`, which starts a Session review and returns at once: a separate headless `claude -p`,
detached so that Claude Code's exit never waits for it, run at the repo's root with the `glossary`
and `adr` skills. It loads the plugin from its own folder too, since the review's session may not
have it otherwise, as where the ended session had it from `--plugin-dir`. A new Config turns it on;
without the key it is off, since it didn't exist before the key (ADR config).

The review reads only the user's and Claude's text, masked as a Retro's is (ADR transcripts),
and at most the last 200,000 characters of it: no tool call or result. It skips a session shorter
than 2,000 characters, which can't have settled much, and a headless one, its own or another
tool's, and a review never starts another. Only what the conversation clearly agreed, and only
about the repo it runs in, is proposed. Anything contested or left open, and a bug or a problem
the session found but didn't fix, is an Inbox item to add, and an item the conversation settled
one to delete (ADR inbox). What is still to do or check on a ticket the conversation worked on, a
check on a device, a PR to merge, a wait on firmware, stays with that ticket and gets no Proposal:
in one project's week, 14 of the review's 37 Inbox items were such, and 44 of the 48 items added
that week never came up again outside going through the Proposals and the Inbox.

A resumed session keeps its id and its Transcript, so its end starts a review of what an earlier
review read already. The plugin keeps, per session, where in the Transcript its last review
stopped, in `sessions/<session>` in the repo's folder, a week as a review's files are: the next
review reads only what follows, under a line that marks what came before as read for context
alone, and skips it as short where it adds less than 2,000 characters. Where the last review
failed, the next one reads again from where that one started. The review is also told the last 50
Proposals the user rejected in the repo, to propose none of them again, and to propose nothing
already waiting in `.about/proposals/`.

It edits nothing in `.about/` itself: it writes Proposals, each a change to the Inbox, the
glossary, an ADR or a PRD that the user accepts, rejects or defers. Each review has an id, when it
started and the first eight characters of the ended session's id, such as
`20261007T174211Z-acf806f4`, and writes its Proposals to `.about/proposals/<id>.md`: a
`## <P1> · <target> · <kind> · <path> · <title>` heading each, the target `inbox`, `glossary`,
`adr` or `prd`, the kind `add`, `edit` or `delete`, a line of why, and the ready edit, the text it
changes under `Before:` and the text it puts there under `After:`, each in a `~~~` fence, which the
plugin also reads as a ``` one, as a reviewer sometimes writes it anyway. Its tools
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
with the plugin's `review-decision`, run with `python3` as session start's line shows it. A Proposal
waits until it is accepted or rejected: deferred, it comes back in the next session, at most twice;
then only accept or reject are offered. When the Before of an edit or a delete is no longer in its
file, the Proposal is stale: it can be accepted only once fixed by hand, and rejecting it is
recommended. A Proposal whose log and file disagree, accepted but not in its file, or in its file
with no decision logged, is shown as a mismatch, and `doctor` counts it. Once each of its Proposals
is accepted or rejected and in its file as decided, the file moves out of the repo into the plugin's
data folder, the repo's `decided/` there, and is kept for good: what a review proposed, beside what
was applied, is what a later measurement judges its quality by.

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

A review that fails must not look like one that found nothing. It replies in JSON (`--output-format
json`), and `runs.log` beside the decisions' log keeps a line per event, split by tabs as that one
is: when, the repo, the review's id, `started`, `ok` or `failed`, its cost in US dollars as Claude
Code counted it, and a detail: how much of the conversation it read, or why it failed, from its
reply or, with none, the first line of its errors. The first session with the user after a review
ended logs its end and is told, once, of a review that failed or that read only the end of its
conversation, to tell the user; `doctor` shows how many failed in the last week and what they cost.

Its session changes nothing else either: there session start creates no Config, picks no Output
style, sets no Status line and writes no Git hook, and no Format on edit runs. A review starts as
the user may be opening their next session, whose session start writes the same settings files.
The Checks a Hook runs still run there, so a tool call of the review's can't show it a Secret;
session start still names the Guidelines. It runs with the user's default model, and may spend
$3 (`--max-budget-usd`): 40 reviews up to 2026-10-17 cost about $0.45 each, $0.81 the dearest, at
Claude Opus 5.5's prices, and the rest leaves room for a dearer default model. A review that
reaches it fails, and is told as any other failure.

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
- A ticket's open check or wait as an Inbox item (until 2026-10-14) — nobody looks for it there,
  and the ticket is where whoever takes it up looks.
- A Proposal of a comment on the ticket — the review can't reach the tracker, and the user would
  post each by hand.
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
- Each review reading the last 200,000 characters of its Transcript (until 2026-10-18) — the review
  of a resumed session read again what an earlier one had, and proposed again what the user had
  already decided.
- Only what an earlier review didn't read, without what came before — an agreement in it that
  refers back, "as we said", loses its subject.
- A failure only in the review's errors file (until 2026-10-18) — on 2026-10-17 two reviews in one
  project failed, on a session limit and on a `claude` logged out, and nothing told them from a
  review that proposed nothing.
- No budget (until 2026-10-18) — a review stuck in a loop spends without a bound, and nothing showed
  what reviews cost.
- A key for the budget — one more setting, as for the model; the costs `runs.log` collects tell
  where to move the constant.
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
- The budget is Claude Code's list price, notional on a subscription, where a review spends the
  session's limit instead (ADR transcripts counts in tokens for that reason); on a dearer default
  model a long review may reach it.
- A session resumed after its mark is deleted, a week on, is read whole again; the rejected
  Proposals and the waiting ones keep most of that from coming back.
- Where a resumed session ends while the review of its earlier part still runs, the new review
  starts where that one stops; if that one then fails, its failure is told but its part is not read
  again.
- `runs.log` grows with every review, as the decisions' log does.
- Revisit when a review proposes something wrong or about another repo, when the costs in
  `runs.log` show the budget far from what reviews spend, or when the share accepted stays low.
