#!/bin/bash
# The shop, with a PRD for the order export whose every part the user has agreed, but whose
# criteria leave out the currency though the shop sells in several (ADR money).
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
mkdir -p .about/prd
cat > .about/prd/order-export.md <<'R'
# Support exports the week's orders as a CSV file

Status: proposed

## Problem

Support retypes the order list into Excel every week to build their reports, about two hours
each time.

## Users

The support team; not customers.

## Success signal

Support stops retyping orders within a month of release.

## Scope

- One button on the order list exports the orders of a date range as CSV.

## Non-goals

- Scheduled or emailed exports.

## Acceptance criteria

- Exporting a week with 3 orders gives a file with a header and 3 rows: order id, customer,
  date, total.
- The totals in the file add up to the total the order list shows for that week.
- Exporting 10,000 orders finishes within 5 seconds.
R
git add .about/prd
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: draft the order export PRD"
