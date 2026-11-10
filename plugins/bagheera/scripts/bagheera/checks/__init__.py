"""The Checks Hooks run, each a function of what Claude Code gives the Hook that runs it (ADR
checks); the commit Checks are `hathi`'s (ADR git-hooks)."""

from __future__ import annotations

from bagheera.checks.bypass import no_git_hook_bypass
from bagheera.checks.context import no_secrets_in_context
from bagheera.checks.git import Error
from bagheera.checks.secrets import ALLOW_SECRET, mask_secrets

__all__ = [
    "ALLOW_SECRET", "HOOK_CHECKS", "Error", "mask_secrets", "no_git_hook_bypass",
    "no_secrets_in_context",
]

# The Checks a Hook runs, by name: each is always on (ADR checks).
HOOK_CHECKS = ["no-git-hook-bypass", "no-secrets-in-context"]
