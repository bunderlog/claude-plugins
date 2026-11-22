---
type: regex
target: { source: file, path: src/features/monitors/views/MonitorView.vue }
pattern: '\b(fetch|useQuery|useMutation|getMonitor|pauseMonitor)\('
match: not_contains
---
