# Glossary format

## .about/glossary.md

```md
# {Project} glossary

{One or two sentences: what the system is and why it exists.}

## Orders

**Order**:
A customer's confirmed request to buy products at agreed prices.
_Avoid_: purchase, basket

**Amendment**:
A correction to a confirmed Order; the Order itself never changes.
_Avoid_: order edit
_In code_: `OrderPatch`

## Unresolved

- **Refund vs Credit** — support says refund, billing code says credit. Settled by: finance
  deciding whether credits can be cashed out.

## Retired terms

- **Basket** — never a separate concept; it is the Cart.
```

- **One concept, one word.** Every rejected synonym goes under `_Avoid_`.
- **One or two sentences.** Define what it **is**, not what it does.
- **Domain terms only.** Nothing a general programmer already knows (cache, retry, timeout),
  however heavily the project uses it.
- **No implementation detail.** A glossary, not a spec or a scratchpad. Code appears only in
  `_In code_` and `## Unresolved`.
- **Topics.** While terms are few, keep one flat list. Once they fall into topics (orders,
  payments…), group them under a subheading per topic.
- Optional trailers, sparingly: `_Planned_:` agreed but not built yet — what's missing;
  `_In code_:` the code's name for it.
- `## Retired terms`: words dropped because the concept doesn't exist, so a reader meeting
  them in old code knows they mean nothing. It and `## Unresolved` stay at the end of the file.

## Several contexts

A context is a part of the system with its own vocabulary, where the same word can mean
something else (`Account` in Ordering vs Billing). Keep one file:

- Each context is a `## Context: <name>` section opening with one sentence on what it covers.
- Topics inside a context go one level down: `###`.
- Terms that mean the same everywhere go under `## Shared`.

```md
## Shared

**Customer**:
A person or organization that places orders.

## Context: Ordering

Receiving and tracking customer orders.

### Orders

**Order**: ...

### Customers

**Account**:
The Customer's login and saved delivery addresses.

## Context: Billing

Invoices and payments.

**Account**:
The ledger of a Customer's charges and payments.
```
