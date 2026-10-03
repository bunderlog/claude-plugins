# A Verification is the plugin's one agent, run by the `verify` skill when the user asks

Date: 2026-10-03

A change can depart from what the project agreed (an ADR, a glossary term, a Guideline's rule, an
Issue's or PRD's acceptance criteria) without breaking a test, and the session that wrote it is the
one least likely to see it. Claude Code's own code review hunts bugs, and its `/verify` runs the
change to see it work; neither knows anything of `.about/`. So the plugin ships one agent,
`agents/verifier.md`, which checks a change against these in a context of its own and reports each
departure with `file:line`. It doesn't hunt bugs, which the code review does.

The `verify` skill runs it with `context: fork` and `agent: baloo:verifier`, waiting for its reply,
so the user has `/baloo:verify`; Claude can also run the agent by its name. Both are for when the
user asks: a Verification is a whole run's tokens, and the Stop check already runs the tests
after each turn that changed something. By default it looks at the current branch's commits since
the default branch, plus the working tree; a commit range, a branch or a PR given overrides that.
It checks the criteria of the Issue or PRD it is given, or else of the one the branch's name, its
commits or its files point to, and says so when it finds none rather than guessing. Checking a
built feature's whole PRD, every criterion's test link, stays the `prd` skill's (ADR prd): a
Verification looks at the criteria one change serves.

Its tools are Read, Grep, Glob and Bash, for git and the tracker's client; that it writes nothing
holds only by its prompt, since a plugin's agent can't set a permission mode and Bash can write. Its
findings are its reply: the session that asked decides with the user what to fix, and sends what is
left for later to the Inbox, as `principles` says for a code review's findings (ADR inbox). What it
can't check by reading, whether the change works when run, it names for `/verify`. It runs with the
user's model, as the Session review does (ADR session-review). No Config key turns it on or off: a
plugin's agent and skill can't be hidden from one project anyway.

Session start's context doesn't reach a subagent, so the plugin adds a `SubagentStart` Hook for
the agent alone (`^baloo:verifier$`): the binary's `subagent-start` gives it the same Guidelines
index session start prints. Where the binary is missing or fails, the agent starts without it and
says it couldn't check the Guidelines.

## Considered options

- Four agents: analyzing an Issue, implementing, reviewing and testing — analyzing is what the
  built-in Explore and the `debugging` Guideline do already, with the conversation the session
  has and an agent lacks; implementing in an agent hides the work from the user, who can no longer
  steer it; testing is the Stop check's and building test-first's, and what remains of it,
  checking the criteria, is this agent's.
- A pipeline from Issue to tested change — each repo's flow is its own, as for `ship`
  (ADR issues).
- Bugs too — one run instead of two, but a copy of the code review in a longer prompt.
- Claude running it by itself after each task — catches more, at a run's cost nearly every time.
- Only the agent, with no skill — no `/baloo:verify`; the user would have to know
  `@agent-baloo:verifier`.
- Only a skill forked onto `general-purpose` — no agent file, but its tools can't be limited.
- The diff put into the prompt by the skill, with no Bash — truly unable to write, but a large
  diff fills the prompt, and a PR or a run by the agent's name has none.
- Writing its findings to the Inbox itself — it would need Edit, and what the session fixes a
  minute later would still land there.
- The agent reading the Config itself, or the caller passing the Guidelines — the first guesses
  the plugin's folder and copies the index's rules into a prompt; the second is forgotten, and a
  run by the agent's name has none.
- `review` for the name — the word is a Session review's, a Retro's and a code review's already
  (ADR inbox).

## Consequences

- The agent's and the skill's descriptions are in every session, the project's using them or
  not.
- A Verification can still write through Bash if its prompt is ignored; the user's permission
  rules are what stop it.
- Revisit when Claude Code lets a plugin's agent set its permissions, or users ask to verify every
  change without asking.
