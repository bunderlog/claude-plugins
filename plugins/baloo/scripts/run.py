"""The plugin's entry script: its Hooks, Git hooks, Status line and skills run it as
`python3 -E -s <plugin>/scripts/run.py <command> ...` (ADR binary). It is written for any python3,
so one older than 3.9 says so rather than failing on newer syntax, on stderr: with exit 2 for
session start, which Claude Code shows the user, and for a command run by hand or by a skill; with
exit 0 for a Git hook, which lets the commit through, as with python3 missing; and not at all for
the other Hooks and the Status line, since exit 2 there would stop a tool call, a prompt or a
turn's end."""

import os
import sys

QUIET = [
    "allow-guideline", "pre-tool-use", "post-tool-use", "session-end", "user-prompt-submit",
    "subagent-start", "status-line",
]

if sys.version_info < (3, 9):
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command in QUIET:
        sys.exit(0)
    sys.stderr.write(
        "baloo: needs python3 3.9 or later, and %s is %d.%d, so the plugin's Checks don't run\n"
        % (sys.executable, sys.version_info[0], sys.version_info[1])
    )
    sys.exit(0 if command == "git-hook" else 2)

here = os.path.dirname(os.path.realpath(__file__))
if sys.path[0] != here:
    sys.path.insert(0, here)

from baloo import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli.main())
