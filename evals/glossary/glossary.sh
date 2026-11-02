#!/bin/bash
# The shop, with a .about/glossary.md of its first terms. Each glossary case's scaffold.sh runs it.
set -euo pipefail
bash "$(dirname "$0")/../adr/shop.sh"
cat > .about/glossary.md <<'R'
# Shop glossary

The shop's backend, where customers order products that Billing charges and Shipping sends.

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
git add .about/glossary.md
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: add the glossary"
