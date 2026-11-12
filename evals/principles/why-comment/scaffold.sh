#!/bin/bash
# The shop, whose invoice taxes its net total once while each printed line shows its own rounded
# tax, and an Issue where the two differ by a cent. The fix rounds each line's tax and sums them:
# the one-line tax on the total it replaces looks tidier, so only a comment keeps it from coming
# back.
set -euo pipefail
bash "$(dirname "$0")/../../adr/shop.sh"
cat > src/shop/invoices/totals.py <<'EOF'
from dataclasses import dataclass


@dataclass
class Line:
    description: str
    price_cents: int
    quantity: int


@dataclass
class Totals:
    net_cents: int
    tax_cents: int
    gross_cents: int


def round_half_up(numerator, denominator):
    return (numerator + denominator // 2) // denominator


def line_tax_cents(line, rate_bp):
    """A line's tax, rounded to the cent, at a rate in basis points (700 is 7%)."""
    return round_half_up(line.price_cents * line.quantity * rate_bp, 10_000)


def invoice_totals(lines, rate_bp):
    net = sum(line.price_cents * line.quantity for line in lines)
    tax = round_half_up(net * rate_bp, 10_000)
    return Totals(net, tax, net + tax)
EOF
cat > src/shop/invoices/render.py <<'EOF'
from shop.invoices.totals import invoice_totals, line_tax_cents


def render(lines, rate_bp, currency):
    out = []
    for line in lines:
        net = line.price_cents * line.quantity
        out.append(f"{line.description}  {net / 100:.2f}  tax {line_tax_cents(line, rate_bp) / 100:.2f}")
    totals = invoice_totals(lines, rate_bp)
    out.append(f"Net {totals.net_cents / 100:.2f}  Tax {totals.tax_cents / 100:.2f}  "
               f"Total {totals.gross_cents / 100:.2f} {currency}")
    return "\n".join(out)
EOF
cat > tests/invoices/test_totals.py <<'EOF'
from shop.invoices.totals import Line, invoice_totals


def test_totals_of_one_line():
    totals = invoice_totals([Line("Mug", 1000, 2)], 1900)
    assert (totals.net_cents, totals.tax_cents, totals.gross_cents) == (2000, 380, 2380)
EOF
mkdir -p .about/issues
cat > .about/issues/invoice-tax.md <<'EOF'
# An invoice's tax total differs from its lines' tax by a cent

2026-11-10

## Symptom

The tax office rejected invoice INV-2291: three lines of tea at 1.10 EUR and 7% each print a tax
of 0.08, 0.24 together, but the invoice's tax total says 0.23. An invoice's tax total must be the
sum of the tax its lines show.

## Acceptance criteria

- An invoice's tax total is the sum of its lines' tax as printed: INV-2291's is 0.24 EUR.
EOF
git add -A
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "feat: total and print invoices"
