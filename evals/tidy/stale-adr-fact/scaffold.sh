#!/bin/bash
# The shop, with an ADR naming a file the bus moved out of.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
cat > .about/adr/bus.md <<'R'
# Events go through the in-process bus

Date: 2026-09-05

Every event is published on the one `Bus` in `src/shop/events.py`, synchronously; a module
subscribes in its constructor. A broker comes only once a module runs in a process of its own.
R
git add .about/adr/bus.md
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: record the bus"
