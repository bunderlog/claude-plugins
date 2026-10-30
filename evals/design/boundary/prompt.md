---
description: Data from outside is parsed once where it comes in, into types that can't hold an illegal value, and the code behind trusts those types.
plugins: ["../../../plugins/baloo"]
max_turns: 30
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit]
---

Add sign-up to the service: `POST /signup` with a JSON body `{"email", "plan", "seats"}`. The plan
is `free`, `pro` or `team`; seats are 1 to 50 and only for `team`, and the other plans have one.
Put the handler and the function that signs an account up in `signup/signup.go`; the account is
stored through `store.Accounts`. No tests yet.
