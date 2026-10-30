#!/bin/bash
# The shop, with one Inbox item ADR integration already settles and one still open.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
cat > .about/inbox.md <<'R'
## Should Ordering call Billing directly?

2026-10-01 · design review

Placing an order could call `BillingClient.charge()` and wait for the result, instead of
publishing an event. Settled by deciding how Ordering and Billing talk.

## Which carrier ships international orders?

2026-10-02 · ops

Shipping sends only domestic parcels today. DHL and FedEx both quoted; DHL is cheaper, FedEx
covers more countries. Settled by picking one.
R
git add .about/inbox.md
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: add two inbox items"
