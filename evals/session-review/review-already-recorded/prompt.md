---
description: A conversation that only restates a decision .about/ already holds proposes nothing and writes no file.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

The conversation that just ended is on stdin. Find what it settled or left open that
.about/ doesn't say yet, and propose each change to .about/ in ./.about/proposals/20261030T120000Z-0e7a1c35.md; edit nothing else, and
never .about/ itself: the user accepts, rejects or defers each proposal later. Use the baloo:glossary and baloo:adr skills for what to check and for the
format of a term or an ADR, but write their result as a proposal. Nobody can answer questions:
propose only what the conversation clearly agreed, and only about this repo. Anything contested or
left open, and a bug or problem it found but didn't fix, is an Inbox item to add to .about/inbox.md: a "## <title>", a line "<YYYY-MM-DD> · session review", then what it is and
what would settle it. What is still to do or check on a ticket the conversation worked on (a check
on a device, a PR to merge, a wait on firmware) stays with that ticket: propose nothing for it. An
item the conversation settled is one to delete. A PRD changes only where
the conversation agreed what the feature is for or how it is checked. Propose nothing already
waiting in .about/proposals/.

Write nothing when there is nothing to propose. Otherwise write the file as:

# Session review 20261030T120000Z-0e7a1c35

## P1 · <target> · <kind> · <path> · <title>

Why: <one line: what in the conversation it comes from>

Before:

~~~markdown
<the text it changes or deletes, copied exactly from the file>
~~~

After:

~~~markdown
<the text it adds, or the text that replaces Before>
~~~

Number them P1, P2… <target> is inbox, glossary, adr or prd, and <path> its file:
.about/inbox.md, .about/glossary.md, .about/adr/<subject>.md or .about/prd/<feature>.md. <kind> is add (After only: the new text, a new file's whole text), edit
(Before and After) or delete (Before only). Keep each Before short but unique in its file. End your
reply with one line per proposal.

The conversation, as stdin holds it:

user: Remind me, can Ordering call Billing directly when an order is placed?

assistant: No. ADR integration says Ordering publishes OrderPlaced and Billing charges the order when it receives it, so an order can be placed while Billing is down. src/shop/ordering/service.py does exactly that.

user: Right, that's what I thought. Keep it that way.
