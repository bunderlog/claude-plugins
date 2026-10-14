"""The plugin's entry script: its Hooks, Git hooks, Status line and skills run it as
`python3 -E -s <plugin>/scripts/run.py <command> ...` (ADR binary). It is written for any python3,
so one older than 3.9 says so rather than failing on newer syntax: session start, on stderr with
exit 2, which Claude Code shows the user; every other command silently, since exit 2 there would
stop a tool call, a prompt or a turn's end."""

import os
import sys

if sys.version_info < (3, 9):
    if sys.argv[1:2] == ["session-start"]:
        sys.stderr.write(
            "baloo: needs python3 3.9 or later, and %s is %d.%d, so no Check runs this session\n"
            % (sys.executable, sys.version_info[0], sys.version_info[1])
        )
        sys.exit(2)
    sys.exit(0)

here = os.path.dirname(os.path.realpath(__file__))
if sys.path[0] != here:
    sys.path.insert(0, here)

from baloo import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli.main())
