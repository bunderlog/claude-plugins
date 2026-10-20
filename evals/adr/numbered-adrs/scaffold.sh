#!/bin/bash
# The shop, its ADRs numbered in docs/adr/ as adr-tools keeps them.
set -euo pipefail
bash "$(dirname "$0")/../shop.sh"
mkdir -p docs/adr
n=1
for name in persistence money api integration catalog; do
  git mv ".about/adr/$name.md" "docs/adr/$(printf '%04d' "$n")-$name.md"
  n=$((n + 1))
done
rmdir .about/adr .about
git -c gc.auto=0 -c maintenance.auto=false -c user.name=eval -c user.email=eval@example.com commit -q -m "docs: number the ADRs"
