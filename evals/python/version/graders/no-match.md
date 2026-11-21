---
type: regex
target: { source: file, path: src/notify/client.py }
pattern: '(^|\n)[ \t]*match[ \t]+[^\n=]*:[ \t]*(#[^\n]*)?\n[ \t]+case\b'
match: not_contains
---
