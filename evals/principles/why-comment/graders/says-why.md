---
type: regex
target: { source: file, path: src/shop/invoices/totals.py }
pattern: '(#[^\n]*|"""[^"]*)(add up|adds up|equal|match|printed|tax office|as shown|shows?\b)'
flags: i
---
