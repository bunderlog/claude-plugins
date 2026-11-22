---
description: A new Vue page keeps its requests out of its component, in a composable it calls.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 40
allowed_tools: [Read, Glob, Grep, Write, Edit]
---

Add a monitor's details page at `/monitors/:id`, in
`src/features/monitors/views/MonitorView.vue`: it shows the monitor's URL and its status, and a
Pause button that pauses it and goes back to the monitors list. Show the status with a new
`src/features/monitors/components/MonitorStatus.vue`, which takes the status and emits `retry`
when a down monitor's badge is clicked. The API calls are already in
`src/features/monitors/services/monitors.ts`. Test the page in
`src/features/monitors/views/MonitorView.test.ts`.
