"""The person's own deny rules on Secrets' files (PRD deny): Claude Code's Read deny rules for
every folder, a second layer under no-secrets-in-context (ADR checks), which session start offers
once per machine to add and doctor names where they are missing. The plugin writes none itself."""

from __future__ import annotations

from typing import List

from bagheera import settings

# The rules: PRD project-setup's list anchored for every folder, and the files
# no-secrets-in-context knows to hold Secrets.
RULES = [
    "Read(//**/.env)", "Read(//**/.env.local)", "Read(//**/.env.*.local)",
    "Read(//**/.env.development)", "Read(//**/.env.production)", "Read(//**/.env.staging)",
    "Read(//**/.env.test)", "Read(//**/.envrc)", "Read(//**/*.pem)", "Read(//**/*.key)",
    "Read(//**/id_rsa)", "Read(//**/id_ed25519)", "Read(~/.ssh/id_*)", "Read(~/.aws/credentials)",
    "Read(~/.netrc)", "Read(~/.docker/config.json)", "Read(~/.config/gh/hosts.yml)",
]


def user_file() -> str:
    """The person's own settings file, where the rules go: settings.json in CLAUDE_CONFIG_DIR, or
    else in ~/.claude/; "" where neither is known."""
    return settings.files("")[settings.USER]


def missing() -> List[str]:
    """The rules neither the person's own settings nor the managed ones deny, in RULES' order. It
    raises ValueError where one of them isn't JSON, or its permissions.deny isn't a list."""
    paths = {settings.USER: user_file(), settings.MANAGED: settings.managed()}
    held: List[str] = []
    for scope, fields in settings.read_all(paths).items():
        permissions = fields.get("permissions", {})
        rules = permissions.get("deny", []) if isinstance(permissions, dict) else None
        if not isinstance(rules, list):
            raise ValueError(f"{paths[scope]}: permissions.deny is not a list")
        held += [r for r in rules if isinstance(r, str)]
    return [r for r in RULES if r not in held]
