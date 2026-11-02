#!/bin/bash
# The shop, with an Issue to cancel an Order that has acceptance criteria.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
mkdir -p .about/issues
cat > .about/issues/cancel-order.md <<'R'
# Cancel a placed Order

2026-10-28

## Symptom

Support can't cancel an Order a customer changed their mind about: it gets charged and shipped
anyway.

## Acceptance criteria

- Canceling a placed Order publishes `OrderCanceled` with the Order's id.
- Canceling an Order that was already canceled raises `ValueError` and publishes nothing.
R
git add .about/issues
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: file the cancel Issue"
