# ADR format

`.about/adr/<subject>.md`: the subject in a word or two (`billing.md`, `git-hooks.md`), kept
stable, since other files cite it ("ADR billing").

```md
# {The subject's decisions, in one line}

Date: YYYY-MM-DD

{Per decision, 1–3 sentences: the context, what was decided, and why.}
```

`Date` is when the ADR last changed. An ADR holds only decisions taken; one still open is an
item in `.about/inbox.md`. That is often enough. Add a section only when it earns its place:

- **Considered options** — rejected alternatives worth remembering, only ones actually
  discussed, and each choice a changed decision dropped, marked `(until YYYY-MM-DD)` with why.
- **Consequences** — non-obvious effects, including the downsides knowingly accepted, and what
  would make us revisit it ("Revisit when …").

What typically qualifies — any kind of decision, not only architecture: domain rules and
invariants that are not obvious or costly to change; architectural shape; how contexts integrate;
technology with lock-in; ownership and scope boundaries (the explicit "no"s too); deliberate
deviations from the obvious path; constraints invisible in code (compliance, partner contracts,
SLAs); a rejected option likely to be proposed again.
