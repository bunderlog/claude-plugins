user: Remind me, can Ordering call Billing directly when an order is placed?

assistant: No. ADR integration says Ordering publishes OrderPlaced and Billing charges the order when it receives it, so an order can be placed while Billing is down. src/shop/ordering/service.py does exactly that.

user: Right, that's what I thought. Keep it that way.
