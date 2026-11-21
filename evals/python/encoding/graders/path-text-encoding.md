---
type: regex
target: { source: file, path: tools/notes.py }
pattern: '\b(read_text|write_text)\((?!(?:[^()]|\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))*\))*\bencoding\s*=)'
match: not_contains
---
