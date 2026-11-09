"""The Checks Hooks run, each a function of what Claude Code gives the Hook that runs it (ADR
checks); the commit Checks are `hathi`'s (ADR git-hooks)."""

from __future__ import annotations

from baloo.checks.bypass import no_git_hook_bypass
from baloo.checks.context import no_secrets_in_context
from baloo.checks.git import Error
from baloo.checks.secrets import ALLOW_SECRET, mask_secrets

__all__ = [
    "ALLOW_SECRET", "HOOK_CHECKS", "Error", "mask_secrets", "no_git_hook_bypass",
    "no_secrets_in_context",
]

# The Checks a Hook runs, by name: each is on without its key under claude-hooks in the Config
# (ADR checks).
HOOK_CHECKS = ["no-git-hook-bypass", "no-secrets-in-context"]
