---
type: regex
target: { source: file, path: src/notify/client.py }
pattern: '^(?![\s\S]*\bfrom\s+__future__\s+import\s+annotations\b)[\s\S]*((:|->)\s*[\w.]+(\[[^\]\n]*\])?\s*\|\s*[\w.]|\bNone\s*\|\s*[\w.])'
match: not_contains
---
