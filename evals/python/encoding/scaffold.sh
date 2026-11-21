#!/bin/bash
# A project with a script that prints the release notes' header, and a CHANGES.md that isn't
# ASCII: read without an encoding, it decodes as cp1252 on Windows.
set -euo pipefail
git init -q -b main
mkdir -p tools
cat > README.md <<'R'
# atlas

Maps for the field team. `python tools/notes.py` prints the release notes.
R
cat > CHANGES.md <<'R'
# Changes

## 2.4.0

- Offline maps for São Paulo and Zürich.
- The legend shows distances in km — or miles, where the device says so.
R
cat > tools/notes.py <<'R'
"""Prints the release notes."""


def main():
    print("Release notes")
    print("=============")


if __name__ == "__main__":
    main()
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Add the release notes script"
