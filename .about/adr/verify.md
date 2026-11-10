# A Verification is louie's verifier, one per source, run by the `verify` Workflow when asked

Date: 2026-11-10

A change can depart from what the project agreed (an ADR, a glossary term, a Guideline's rule, an
Issue's or PRD's acceptance criteria) without breaking a test, and the session that wrote it is the
one least likely to see it. Claude Code's own code review hunts bugs, and its `/verify` runs the
change to see it work; neither knows anything of `.about/`. So louie ships one agent,
`agents/verifier.md`, which checks a change against these in a context of its own and reports each
departure with `file:line`. It doesn't hunt bugs, which the code review does.

The `verify` Workflow runs four of it at once, one per source: the ADRs, the glossary, the
Guidelines and the acceptance criteria, each told its one source and returning its findings in a
schema; the script, not a model, joins them into one report and decides the verdict: it fails on a
departure that blocks or a criterion not met (PRD delivery). So the user has `/louie:verify`, and
`deliver` runs the same Workflow as a stage. Where the session has no Workflow tool, as on Pro until
Workflows are turned on, Claude runs the agent by its name instead, checking every source in one
context. A Verification runs only when the user asks or agrees, or as a stage of a `deliver` run
they started, as it is a whole run's tokens. Claude offers one, in a line and
once, at the end of a task that serves an Issue or a PRD with acceptance criteria, before its commit
or PR: there it has criteria to check against, and few tasks have one. The Workflow's description
says so, and a line in `principles`' On every task, which session start prints in every session
(ADR guidelines): on 2026-11-02 the description alone made Claude offer it in 3 of 3 runs on
Opus but 0 of 3 on Sonnet, the line in 3 of 3 on both, and without the plugin in none
(`evals/verify/offer`). By default it looks at the current branch's
commits since the default branch, plus the working tree; a commit range, a branch or a PR given
overrides that. It checks the criteria of the Issue or PRD it is given, or else of the one the
branch's name, its commits or its files point to, and says so when it finds none rather than
guessing. Checking a built feature's whole PRD, every criterion's test link, stays the `prd` skill's
(ADR prd): a Verification looks at the criteria one change serves.

Its tools are Read, Grep, Glob and Bash, for git and the tracker's client; that it writes nothing
holds only by its prompt, since a plugin's agent can't set a permission mode and Bash can write. Its
findings are its reply: the session that asked decides with the user what to fix, and sends what is
left for later to the Inbox, as `principles` says for a code review's findings (ADR inbox). What it
can't check by reading, whether the change works when run, it names for `/verify`. It runs with the
user's model, as the Session review does (ADR session-review). Nothing turns it off but louie
itself: a plugin's agent and Workflow can't be hidden from one project anyway.

Session start's context doesn't reach a subagent, so the plugin adds a `SubagentStart` Hook for the
agent alone (`^louie:verifier$`), a Workflow's agents too where Claude Code starts them as
subagents: the plugin's `subagent-start` gives it the same Guidelines index session start prints.
Where `python3` is missing or the plugin fails, the agent starts without it and says it couldn't
check the Guidelines.

## Considered options

- Four agents: analyzing an Issue, implementing, reviewing and testing — analyzing is what the
  built-in Explore and the `debugging` Guideline do already, with the conversation the session
  has and an agent lacks; implementing in an agent hides the work from the user, who can no longer
  steer it; testing is the project's checks' and building test-first's, and what remains of it,
  checking the criteria, is this agent's.
- A pipeline from Issue to tested change — each repo's flow is its own, as for `ship`
  (ADR issues).
- Bugs too — one run instead of two, but a copy of the code review in a longer prompt.
- Claude running it by itself after each task — catches more, at a run's cost nearly every time.
- Run only when the user asks, never offered (until 2026-11-02) — in about 200 sessions in five
  projects up to 2026-10-30 neither the skill nor the agent ever ran, by the user or by Claude.
- Offered after every non-trivial edit of code — catches more, but offered nearly every session,
  it soon goes unread.
- Offered before a PR only — never, in a project that commits straight to `main`.
- Only the agent, with no skill — no `/louie:verify`; the user would have to know
  `@agent-louie:verifier`. Where Workflows are off, that is how it is, and Claude offers the agent
  by name.
- The `verify` skill running the one agent with `context: fork` (until 2026-11-10) — one context
  read every source, the agent judged its own verdict, and `deliver` would have needed its own
  copy of the Review.
- Only a skill forked onto `general-purpose` — no agent file, but its tools can't be limited.
- The diff put into the prompt by the skill, with no Bash — truly unable to write, but a large
  diff fills the prompt, and a PR or a run by the agent's name has none.
- Writing its findings to the Inbox itself — it would need Edit, and what the session fixes a
  minute later would still land there.
- The agent finding the Guidelines itself, or the caller passing them — the first guesses
  the plugin's folder and copies the index's rules into a prompt; the second is forgotten, and a
  run by the agent's name has none.
- `review` for the name — the word is a Session review's, a Retro's and a code review's already
  (ADR inbox).

## Consequences

- The agent's and the Workflow's descriptions are in every session, the project's using them or
  not.
- A Verification can still write through Bash if its prompt is ignored; the user's permission
  rules are what stop it.
- A task that serves an Issue or PRD ends with one more line, the offer, though the user may
  decline it every time.
- Revisit when Claude Code lets a plugin's agent set its permissions, users ask to verify every
  change without asking, or a measurement finds the offer declined nearly every time or never
  made.
