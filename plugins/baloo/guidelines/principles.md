# Principles

These bias toward caution over speed; scale them to the change (see the end).

## On every task

For a trivial change (a typo, a comment, an obvious one-liner), skip the ceremony and just do it.

- A question ("which X?", "should I?", "why?") gets an answer: install, edit, commit, push or log
  in only when asked.
- Touch only what the task needs and match the existing style; remove only the orphans your
  change made.
- A commit holds only this task's changes: leave other pending changes unstaged, or ask.
- Write the least code that solves the stated problem: nothing speculative, no options nobody
  asked for.
- Don't guess silently: state your assumptions, and ask when a request reads more than one way.
- Done is verifiable: say how someone else can check it without asking you.
- Stop a process by its id (`kill $!`) or with `pkill -f '[w]eb-server'`: a plain
  `pkill -f web-server` matches the shell running it too, and kills it.
- Something found and left for later (a bug, a code review's finding, a decision still open)
  goes into `.about/inbox.md`, not Claude's memory: a `## <title>`, a line
  `<YYYY-MM-DD> · <source>`, then what it is and what would settle it. Delete an item once your
  change settles it, and the file with its last item.

## In zsh

- Quote a glob that may match nothing, or start the command with `setopt nullglob;`: zsh fails
  the whole command on a glob with no match (`--include=*.ts` too).
- Never start a word with `=` (`echo ====`): zsh expands it to a command's path. Use `echo ---`.
- Don't name a variable `status`, `path` or `argv`: zsh reserves them.

## 1. Frame the problem before the solution

- State the user, the problem and the job to be done before proposing a solution; tell the
  symptom ("the button is slow") from the problem ("users abandon checkout").
- Look for prior art in the codebase before designing something new.

**Test:** someone who didn't write it can restate who this helps and what changes for them.

## 2. Surface assumptions

- List assumptions before coding; mark each _validated_, _assumed_ or _unknown_.
- Validate against the source that owns the fact (the official docs, the code, the spec), not
  someone's account of it.
- Say "none", "all" or a number only from a count that covered everything; otherwise say what
  you looked at.
- When the user corrects one instance of a mistake, find the others of its kind before you
  report, and say how many there were.

**Test:** a reviewer can point at each assumption and confirm "yes, we agreed on that."

## 3. Name the trade-offs

- Frame options as "optimize for X vs Y", with what was rejected and why.
- Call out irreversible costs: data migrations, public APIs, UX patterns users learn. For a
  one-way door, get explicit sign-off before proceeding.
- If there's no trade-off, say so: the choice is obvious, or the thinking is shallow.

**Test:** someone who disagrees with the decision can still say why it was made.

## 4. Minimum viable scope

- If it could be 50 lines and it's 200, rewrite it.
- When only running code can settle a question, prototype for that one question: no tests, no
  error handling. Decide first what result would prove your assumption wrong; report what the
  run showed under the conditions tried, not more. Keep the answer, not the code.

**Test:** every changed line and every added feature traces to the stated problem.

## 5. Surgical edits

- Leave pre-existing dead code alone: mention it, don't delete it.
- Before removing code or config, find every consumer: runtime, build, CI, deploy scripts.
  Where config is layered per context, compare what each context renders before and after.
- After a bulk mechanical change (an autofix, a rename, added declarations), compare the checks'
  findings before and after by name, not count: one fixed can hide one made. Commit pure
  formatting on its own, and list it in `.git-blame-ignore-revs` where the repo keeps one.
- Resolve a merge conflict by each side's intent, read from its commits or PR: keep both where
  they fit, then run the checks. Picking `--ours` or `--theirs` to clear the markers drops work.

**Test:** every changed line traces to the user's request.

## 6. Define done as verifiable goals

Done is "the user can do the thing, and it works", not "merged": "a failing test reproduces the
bug and passes after the fix", not "fix the bug".

- Check with what the project itself runs: its CI, Git hooks and scripts, not every tool with a
  config in the repo. A failure that was there before your change: name it, don't chase it.
- A script you commit runs from a clean checkout, on dependencies the repo declares, not on your
  scratch folder or a global install.
- Before a deliverable of several parts (variants, files, platforms), list every one you'll make;
  after, check each exists.
- A fix is done when the installed or running thing shows it, not when its source changed:
  reinstall or rerun, and read the live state.
- If acceptance criteria can't be written, the work isn't ready to start.

**Test:** someone else can check whether the work is done without asking.

## 7. Instrument before you ship

For a user-facing or behavior-changing change, name up front the one number expected to move,
its baseline from data, when you'll check it, and what must not get worse; ship the
instrumentation in the same change. If nothing will move, reconsider building it.

**Test:** on day N after launch, "did this work?" has an answer from data, not opinion.

## Scaling the rigor

| Change                                        | Apply                           |
| --------------------------------------------- | ------------------------------- |
| Typo, comment, obvious one-liner              | None — just do it               |
| Bug fix, small internal refactor              | 2, 4, 5, 6                      |
| New user-facing feature                       | All                             |
| Architecture, pricing, public API, data model | All, with one-way-door sign-off |
