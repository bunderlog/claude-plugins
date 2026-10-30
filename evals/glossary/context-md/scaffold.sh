#!/bin/bash
# The shop, its vocabulary in a CONTEXT.md at the root.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
cat > CONTEXT.md <<'R'
# Shop

The shop's backend: ordering, billing, catalog and shipping.

## Language

**Order**:
What a customer places for one or more Products, paid once.
_Avoid_: basket, cart

**Charge**:
Billing taking an Order's amount from the customer's card.
_Avoid_: payment, transaction

**Shipment**:
The parcel Shipping sends for a paid Order.
_Avoid_: delivery
R
git add CONTEXT.md
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: add the shop's vocabulary"
