---
description: A PRD goes to .about/prd/ with Status proposed while a part is open, and "fast" becomes a criterion a test can pass or fail.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Write a PRD for exporting orders to CSV. Support staff retype the order list into Excel every
week to build their reports. The export should be fast and easy to use.
