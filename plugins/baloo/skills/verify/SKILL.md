---
name: verify
description: Verify a change against what the project agreed — its ADRs, glossary, Guidelines, and the acceptance criteria of its Issue or PRD — in a separate agent that didn't write it, when the user asks to verify or check a change against the project's decisions or criteria. Offer it, in a line and once, at the end of a task that serves an Issue or a PRD with acceptance criteria, before its commit or PR, and run it only if the user agrees. Takes a commit range, a branch, a PR, an Issue or a PRD; by default the current branch and the working tree. Not for hunting bugs, which a code review does, for whether the change works when run, which Claude Code's /verify checks, or for a built feature's whole PRD, which is the prd skill's.
context: fork
agent: baloo:verifier
background: false
---

Verify the change, as your instructions say. What the user named, if anything: $ARGUMENTS
