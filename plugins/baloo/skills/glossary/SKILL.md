---
name: glossary
description: Build and sharpen the project's domain vocabulary while designing — naming or renaming a concept, two words in play for one thing, a vague or overloaded term, an unclear boundary between concepts. Challenges terms against .about/glossary.md, stress-tests them with edge cases and the code, and records entries the moment they settle. Not for merely reading the glossary for vocabulary.
---

# Glossary

You are changing the project's language, not consuming it. Make it sharper; don't just agree.

## File

`.about/glossary.md` at the git repo's root ([format](format.md)). Read it before you start;
create it with the first entry. With several contexts (a monorepo's projects among them),
record a term under the `## Context: <name>` the discussion is about; ask if unclear. The
project's own conventions win over these defaults.

## Check

Call out a clash with the glossary at once: "The glossary says Filter — you said rule. Same
thing, or new?" If the topic touches an item in `## Unresolved`, settle it now.

## Probe

For every new or shifting term:
- Vague or overloaded? Propose one precise word: "account — the Customer or the User?"
- A one-sentence definition that doesn't use the term itself.
- What it is *not*: the nearest neighbour concept and where the line is (a free order? an
  empty cart?).
- Lifecycle: how it's created, its states, who may change it, when it stops being itself
  (cancelled? deleted?).

Stress-test it with borderline cases: "An order ships in two parcels — one Order or two?"
Reach for:
- split and merge: one X or two? when are two X the same X?
- how many: can there be zero, one, many? must it belong to exactly one?
- other viewpoints: do support or billing call it something else?

Check the code as well: a term the code uses differently, or one concept named differently
across modules, is the most valuable finding. A case the glossary can't answer is a finding too:
put it in `## Unresolved`, don't paper over it. Ask a few pointed questions at a time, not a
questionnaire.

## Name

- The users' word beats the code's word. If the code calls the concept something else, don't
  rename the code right away: record the term as users say it and note the code's name in
  `_In code_`.
- Never silently pick a winner: two words genuinely in play go to `## Unresolved`; once
  settled, the loser moves to `_Avoid_`.
- Price a rename first. Names in contracts the project doesn't own or can't cheaply change
  (external APIs and schemas, stored data, public URLs, events) stay — map them at the edge.
  If a term is wrong in one layer only, fix that layer.

## Record

Write the entry the moment it's agreed — don't batch — and tell the user in one line what
changed.
