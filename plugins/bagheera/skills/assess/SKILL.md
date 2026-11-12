---
name: assess
description: Report how useful each part of bunderlog is and how well it works, from the sessions on this machine — when the user asks how bunderlog's plugins are doing, whether a Check, a skill or a Guideline pays off, or to label a Check's denials. Runs the plugin's report, which changes nothing in the project, and labels a denial real or false when the user says which. Not for a Retro of how sessions went.
---

# Assess

From the project folder, run
`CLAUDE_PLUGIN_DATA='${CLAUDE_PLUGIN_DATA}' python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py'
assess`, with `--days <n>` for another window than 30 days and `--repo <part of its name>` for one
repo. The first run also counts the sessions whose Transcripts are still on disk, which takes a
while.

Answer what the user asked from the report: each figure names the PRD or ADR it decides for, and
the figure in brackets is the window before. Say what moved, and what a figure suggests keeping,
changing or dropping; the decision is the user's.

For the denials to label, show each with its call and ask, a few at a time with the
AskUserQuestion tool, whether it kept a Secret out or a command from skipping the Git hooks (real),
or stopped harmless work (false). Store each answer with the same command's
`assess label <session> <call> real|false`.
