---
name: doctor
description: Show baloo's state in this repo and what is wrong with it — when the user asks what baloo has on, which version runs, or why a Check, a Git hook, the Stop check or a Guideline didn't run. Runs the binary's doctor, which only reads. Not for changing the Config.
---

# Doctor

From the project folder, run
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' sh '${CLAUDE_PLUGIN_ROOT}/scripts/loader' doctor`.

Exit 1 means it found problems, listed first, each with what fixes it; exit 2 with a `baloo:`
line on stderr means the Loader couldn't run the binary, and that line says why. Answer what the
user asked from its output: the problems and their fixes first, then only the part of the state
the question is about. A fix is mostly the next session start; a file to move or a Config key to
change is the user's call, so name it rather than doing it.
