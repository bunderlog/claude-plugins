---
type: regex
target: { source: file, path: signup/signup.go }
pattern: 'func\s+(\([^)]*\)\s*)?(?!Parse|parse)\w+\([^)]*\bplan\s+string'
match: not_contains
---
