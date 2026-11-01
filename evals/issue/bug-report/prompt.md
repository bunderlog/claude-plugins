---
description: A bug becomes an Issue in .about/issues/ with its symptom, evidence and acceptance criteria in the description, and the guessed cause in a comment of its own.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

File an issue: orders over 1,000 EUR never ship. The log shows `POST /charges 402` for them and
then nothing, no OrderPaid. I think the provider wants 3-D Secure above that amount, but I'm not
sure.
