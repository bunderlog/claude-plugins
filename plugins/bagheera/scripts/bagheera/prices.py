"""Anthropic's list prices of its models, which the Assessment counts a Workflow run's cost at
(PRD assessment)."""

from __future__ import annotations

import re
from typing import Optional, Tuple

# The day the prices below were read from Anthropic's price list,
# https://platform.claude.com/docs/en/about-claude/pricing; read them again for a new model.
READ = "2026-11-16"

# US dollars per million tokens, by model id: input, output, cache written (the 5-minute write,
# the only one Claude Code's agents were seen making) and cache read, at global routing.
# claude-haiku-5-5 is left out: its price depends on each request's prompt length, which a sum of
# tokens no longer tells, so it counts tokens only.
_PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 5.0, 0.20),
    "claude-opus-5": (5.0, 25.0, 6.25, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0, 2.50, 0.10),
    "claude-sonnet-5": (2.0, 10.0, 2.50, 0.20),
    "claude-haiku-4-5": (1.0, 5.0, 1.25, 0.10),
}

# The date some model ids end in, `claude-haiku-4-5-20251001`.
_DATED = re.compile(r"-\d{8}$")

_Price = Tuple[float, float, float, float]


def _price(model: str) -> Optional[_Price]:
    """The prices of the model `model`, as _PRICES gives them; None for a model with no price."""
    return _PRICES.get(model) or _PRICES.get(_DATED.sub("", model))


def cost(model: str, tokens: Tuple[int, int, int, int]) -> Optional[float]:
    """What `tokens` (input, output, cache written, cache read) of the model `model` cost in US
    dollars; None for a model with no price."""
    p = _price(model)
    if p is None:
        return None
    return sum(n * each for n, each in zip(tokens, p)) / 1_000_000
