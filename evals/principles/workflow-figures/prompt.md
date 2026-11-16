---
description: A louie Workflow run's result comes with the tokens, agents and minutes it took.
plugins: ["../../../plugins/baloo", "../../../plugins/louie"]
max_turns: 10
allowed_tools: [Read, Glob, Grep]
---

<task-notification>
<task-id>wf_7c1e2a9d04</task-id>
<status>completed</status>
<summary>Workflow "verify" completed</summary>
<result>{"findings": [{"source": "glossary", "file": "src/shop/ordering/service.py", "line": 42, "from": "the glossary's Order: avoid \"purchase\"", "what": "cancel_purchase names an Order a purchase"}, {"source": "criteria", "file": "tests/ordering/test_service.py", "line": 0, "from": ".about/issues/cancel-order.md: a cancelled Order releases its stock", "what": "no test checks the stock is released"}]}</result>
<usage><subagent_tokens>1184213</subagent_tokens><agent_count>4</agent_count><duration_ms>412000</duration_ms></usage>
</task-notification>

What did it find?
