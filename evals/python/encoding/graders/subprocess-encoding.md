---
type: regex
target: { source: file, path: tools/notes.py }
pattern: '\b(run|check_output|check_call|call|Popen)\((?=(?:[^()]|\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))*\))*\b(text|universal_newlines)\s*=\s*True)(?!(?:[^()]|\((?:[^()]|\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))*\))*\bencoding\s*=)|\b(getoutput|getstatusoutput|popen)\('
match: not_contains
---
