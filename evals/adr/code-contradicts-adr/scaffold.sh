#!/bin/bash
# The shop, where express checkout charges by calling Billing, against ADR integration.
set -euo pipefail
bash "$(dirname "$0")/../shop.sh"
cat > src/shop/ordering/express.py <<'PY'
from shop.ordering.service import Order


class ExpressCheckout:
    """One-click orders for returning customers."""

    def __init__(self, repository, billing):
        self.repository = repository
        self.billing = billing

    def place(self, order: Order):
        self.billing.charge(order.customer, order.total_cents, order.currency)
        self.repository.save(order)
PY
git add src/shop/ordering/express.py
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "feat: express checkout"
