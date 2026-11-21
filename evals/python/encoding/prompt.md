---
description: A text file or a command's output read in Python names its encoding, so the script reads it the same on every machine.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Write, Edit]
---

Make `tools/notes.py` print, under its header, the text of `CHANGES.md` and then the last 10
commits, as `git log --oneline -10` shows them. No tests yet.
