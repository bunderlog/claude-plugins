#!/bin/bash
# A shop's repo of a few modules and ADRs, where ADR integration, among others, says Ordering
# reaches Billing only by events. Each case's scaffold.sh runs it in the run's workspace.
set -euo pipefail
git init -q -b main
mkdir -p .about/adr src/shop/ordering src/shop/billing src/shop/catalog src/shop/shipping tests

cat > README.md <<'EOF'
# shop

The shop's backend: ordering, billing, catalog and shipping, in one Python package.

    python -m pytest
EOF

cat > .about/adr/integration.md <<'EOF'
# The modules talk through events on the bus, not by calling each other

Date: 2026-09-01

Ordering never calls Billing: it publishes `OrderPlaced`, and Billing charges the order when it
receives it, so an order can be placed while Billing is down, and Billing retries a failed charge
on its own. Shipping starts on `OrderPaid` the same way.
EOF

cat > .about/adr/persistence.md <<'EOF'
# Each module owns its tables in one PostgreSQL database

Date: 2026-08-20

One database, a schema per module; no module reads another's tables, it asks by event or by the
module's own query functions.
EOF

cat > .about/adr/money.md <<'EOF'
# Amounts are integer minor units with a currency

Date: 2026-08-22

A price or a charge is an `int` of cents and an ISO currency code, never a float, so sums are exact.
EOF

cat > .about/adr/api.md <<'EOF'
# The public API is versioned in the path

Date: 2026-08-25

`/v1/...`; a breaking change is a new version, and the old one stays six months.
EOF

cat > .about/adr/catalog.md <<'EOF'
# The catalog is read from a nightly export, not edited in the shop

Date: 2026-09-03

Products come from the ERP's nightly export; the shop never writes a product.
EOF

touch src/shop/__init__.py src/shop/ordering/__init__.py src/shop/billing/__init__.py \
  src/shop/catalog/__init__.py src/shop/shipping/__init__.py

cat > src/shop/bus.py <<'EOF'
from collections import defaultdict


class Bus:
    def __init__(self):
        self.handlers = defaultdict(list)

    def subscribe(self, event, handler):
        self.handlers[event].append(handler)

    def publish(self, event, payload):
        for handler in self.handlers[event]:
            handler(payload)
EOF

cat > src/shop/ordering/service.py <<'EOF'
from dataclasses import dataclass


@dataclass
class Order:
    id: str
    customer: str
    total_cents: int
    currency: str


class OrderService:
    def __init__(self, bus, repository):
        self.bus = bus
        self.repository = repository

    def place(self, order: Order):
        self.repository.save(order)
        self.bus.publish("OrderPlaced", order)
EOF

cat > src/shop/billing/client.py <<'EOF'
class PaymentError(Exception):
    pass


class BillingClient:
    """The payment provider's API."""

    def __init__(self, http):
        self.http = http

    def charge(self, customer, amount_cents, currency):
        r = self.http.post("/charges", {"customer": customer, "amount": amount_cents,
                                        "currency": currency})
        if r.status != 201:
            raise PaymentError(r.status)
        return r.json()["id"]
EOF

cat > src/shop/billing/consumer.py <<'EOF'
from shop.billing.client import PaymentError


class ChargeOnOrderPlaced:
    def __init__(self, bus, client, retries):
        self.bus = bus
        self.client = client
        self.retries = retries
        bus.subscribe("OrderPlaced", self.handle)

    def handle(self, order):
        try:
            charge = self.client.charge(order.customer, order.total_cents, order.currency)
        except PaymentError:
            self.retries.later(order)
            return
        self.bus.publish("OrderPaid", {"order": order.id, "charge": charge})
EOF

cat > src/shop/catalog/products.py <<'EOF'
def load_export(rows):
    return {row["sku"]: {"name": row["name"], "price_cents": int(row["price_cents"])} for row in rows}
EOF

cat > src/shop/shipping/consumer.py <<'EOF'
class ShipOnOrderPaid:
    def __init__(self, bus, carrier):
        self.carrier = carrier
        bus.subscribe("OrderPaid", self.handle)

    def handle(self, paid):
        self.carrier.book(paid["order"])
EOF

cat > tests/test_ordering.py <<'EOF'
from shop.bus import Bus
from shop.ordering.service import Order, OrderService


class Repo:
    def __init__(self):
        self.saved = []

    def save(self, order):
        self.saved.append(order)


def test_place_publishes_order_placed():
    bus, seen = Bus(), []
    bus.subscribe("OrderPlaced", seen.append)
    order = Order("o1", "c1", 1999, "EUR")
    OrderService(bus, Repo()).place(order)
    assert seen == [order]
EOF

# The rest of a real shop: modules, views and their tests, so .about/ is a folder among many.
for module in accounts carts coupons invoices inventory pricing promotions reviews search wishlists; do
  mkdir -p "src/shop/$module" "tests/$module"
  touch "src/shop/$module/__init__.py"
  for part in models views queries handlers serializers validators permissions; do
    printf 'def %s_%s():\n    return None\n' "$module" "$part" > "src/shop/$module/$part.py"
    printf 'from shop.%s.%s import %s_%s\n\n\ndef test_%s_%s():\n    assert %s_%s() is None\n' \
      "$module" "$part" "$module" "$part" "$module" "$part" "$module" "$part" > "tests/$module/test_$part.py"
  done
done

git add -A
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "feat: place, charge and ship orders"
