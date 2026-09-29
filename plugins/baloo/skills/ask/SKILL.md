---
name: ask
description: Interview the user about a plan or design before building it — when the user asks to be interviewed, grilled or questioned, to stress-test a plan, or to settle what's still open before starting a feature or change. Maps the decisions the plan depends on, asks the ready ones a few at a time as multiple-choice questions with a recommended answer, looks facts up instead of asking, and ends with the decision list the user confirms. Not for a single term or decision, or for work that's already settled.
---

# Ask

Question the user about a plan until every decision it depends on is settled, before anything
is built. The decisions are the user's; finding facts is your job.

Read the request, any spec, the code involved, and the project's glossary and ADRs (e.g.
`.about/`). Don't ask what they already answer.

## 1. Map

List the open decisions, each with the decisions it depends on, most consequential first:

1. **Shape** — answers that change the data model, the interfaces or the approach.
2. **Behaviour** — edge cases, failure modes, defaults, permissions, who can reach what's built.
3. **Polish** — names, wording, cosmetics: propose these, don't ask.

A decision is ready once every decision it depends on is settled. Look up the facts a question
needs (how the code does it, what a tool supports), handing a slow search to a subagent, and
keep asking the rest meanwhile.

## 2. Ask

In each round, ask the ready decisions a few at a time, most consequential first, with the
AskUserQuestion tool: each question says in a line why it matters; each option, two or three
concrete ones, gives its trade-off; your recommendation comes first, marked "(Recommended)".
Without the tool, write each as:

```
**Q1. <title>** — why it matters, in a line or two; two or three concrete options.
→ Recommended: <option>, because <reason>.
```

Then wait for the answers. "You decide" is an answer: your recommendation stands, marked as
yours. After each round, update the map: settled decisions make others ready, and an answer can
open new ones. An answer that contradicts an earlier one, an accepted ADR or the code is a
finding: name both sides and ask which holds; never silently take the newest. Every few rounds,
restate what's settled as one short list.

## 3. Stop

Stop when no open decision would change the approach: what's left is cheaper to settle while
building than to ask now. Say so, and name what's left.

End with the decision list: each decision and its answer, marking the ones you decided. Ask the
same way whether to confirm it or change something. Done when the user confirms it; build
nothing before then, and don't commit.
