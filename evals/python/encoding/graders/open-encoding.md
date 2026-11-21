---
type: regex
target: { source: file, path: tools/notes.py }
pattern: '\bopen\((?!(?:[^()]|\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))*\))*\bencoding\s*=)(?!(?:[^()]|\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))*\))*[''"][rwxat+]*b[rwxat+]*[''"])'
match: not_contains
---
