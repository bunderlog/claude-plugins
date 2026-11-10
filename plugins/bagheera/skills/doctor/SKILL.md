---
name: doctor
description: Show bagheera's state in this repo and what is wrong with it — when the user asks what bagheera has on, which version runs, or why a Check didn't run, or what an earlier baloo left in the clone. Runs the plugin's doctor, which only reads. Not for changing a setting.
---

# Doctor

From the project folder, run
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' doctor`.

Exit 1 means it found problems, listed first, each with what fixes it; exit 2 with a `bagheera:` line
on stderr means it couldn't run, and that line says why; no `python3` at all means no Hook of the
plugin runs either, which Python 3.9 or later fixes. Answer what the user asked from its output: the
problems and their fixes first, then only the part of the state the question is about. A fix is
mostly the next session start; a file to remove or a setting to change is the user's call, so name
it rather than doing it.
