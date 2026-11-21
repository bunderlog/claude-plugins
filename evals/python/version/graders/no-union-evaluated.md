---
type: regex
target: { source: file, path: src/notify/client.py }
pattern: '\b(isinstance|issubclass|cast)\([^)\n]*\||(^|\n)[A-Za-z_]\w*\s*(:\s*[\w.]+\s*)?=\s*[\w.]+(\[[^\]\n]*\])?\s*\|\s*[\w.]|=\s*[\w.]+(\[[^\]\n]*\])?\s*\|\s*None\b'
match: not_contains
---
