#!/bin/bash
# The shop, with an Inbox item on the international carrier, left open.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
cat > .about/inbox.md <<'R'
# Inbox

## International carrier

2026-10-20 · session review

Shipping sends only domestic parcels; DHL and FedEx both quoted for international orders. DHL is
cheaper, FedEx covers more countries. Settled once sales names the first target countries.
R
git add .about/inbox.md
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: note the carrier question"
