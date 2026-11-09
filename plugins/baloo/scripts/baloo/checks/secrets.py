"""The kinds of Secret the plugin knows, to mask them in a Transcript (ADR transcripts), and what
an Env file is, for no-secrets-in-context."""

from __future__ import annotations

import re

from baloo import names

# Marks a false alarm of a commit's Secrets check, `hathi`'s now, which still passes baloo's mark;
# no-secrets-in-context keeps Claude from adding it.
ALLOW_SECRET = names.PLUGIN + ":allow-secret"

# Each kind of Secret, by its name; the first that matches names it, so the more specific come
# first.
_SECRET_KINDS = [
    (what, re.compile(pattern, re.A))
    for what, pattern in [
        ("a private key", r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----"),
        ("an AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        ("a GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"),
        ("a Slack token", r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
        ("a Stripe live key", r"\b[rs]k_live_[A-Za-z0-9]{20,}"),
        ("an Anthropic API key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
        ("an OpenAI API key", r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
        ("a Google API key", r"\bAIza[0-9A-Za-z_-]{35}"),
        ("a JWT", r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}"),
        # The password in a URL, between `://user:` and `@`, unless it is a placeholder: `$VAR`,
        # `${VAR}`, `<password>`, `****`.
        ("a password in a URL", r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\s:/@]*:[^\s/@$<{*][^\s/@]*@"),
    ]
]

# An Env file: .env, .env.local, prod.env, .envrc…
_ENV_FILE = re.compile(r"(^|/)(\.env(\.[^/]*)?|\.envrc|[^/]*\.env)\Z")
# An Env file's template, meant to be committed.
_TEMPLATE = re.compile(r"\.(example|sample|template|dist)\Z")
def mask_secrets(text: str, mask: str) -> str:
    """`text` with each Secret of a kind it knows replaced by `mask`."""
    for _, pattern in _SECRET_KINDS:
        text = pattern.sub(lambda _: mask, text)
    return text


def is_env_file(path: str) -> bool:
    """Whether the file at `path` is an Env file, not a template of one."""
    return bool(_ENV_FILE.search(path)) and not _TEMPLATE.search(path)
