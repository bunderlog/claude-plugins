"""The Check no-secrets-in-commits, and the kinds of Secret it knows."""

# cspell:ignore AKIA pousr abprs bxox ACMR

from __future__ import annotations

import re
from typing import List

from baloo import names
from baloo.checks.git import git

# Marks a false alarm of no_secrets_in_commits: on a line, or on an Env file's first line.
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
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)", re.A)

# The git diff of the staged files added, copied, changed or renamed, as git itself prints it,
# whatever the repo's config says of diffs.
_STAGED = ["diff", "--cached", "--no-ext-diff", "--no-textconv", "--no-color", "--diff-filter=ACMR"]


def no_secrets_in_commits(dir: str) -> List[str]:
    """The Check baloo:no-secrets-in-commits (pre-commit): the Leaks the staged changes of the repo
    `dir` would commit, each as `<path>: an env file…` or `<path>:<line>: <what>`, never the Secret
    itself. A line with ALLOW_SECRET on it passes, and an Env file with it on its first line, whose
    lines are still looked through. It raises an Error where git fails, such as outside a repo."""
    found = []
    for path in git(dir, *_STAGED, "--name-only", "-z").removesuffix("\0").split("\0"):
        if not is_env_file(path):
            continue
        first = git(dir, "cat-file", "blob", ":" + path).split("\n", 1)[0]
        if ALLOW_SECRET not in first:
            found.append(
                f"{path}: an env file; keep it out of git, or put {ALLOW_SECRET} on its first line"
            )
    return found + _scan(git(dir, *_STAGED, "--no-prefix", "-U0"))


def mask_secrets(text: str, mask: str) -> str:
    """`text` with each Secret of a kind no_secrets_in_commits knows replaced by `mask`."""
    for _, pattern in _SECRET_KINDS:
        text = pattern.sub(lambda _: mask, text)
    return text


def is_env_file(path: str) -> bool:
    """Whether the file at `path` is an Env file, not a template of one."""
    return bool(_ENV_FILE.search(path)) and not _TEMPLATE.search(path)


def _scan(diff: str) -> List[str]:
    """`<path>:<line>: <what>` for each Secret on a line the diff `diff` adds."""
    found = []
    path = ""
    line, header = 0, False
    for text in diff.split("\n"):
        if text.startswith("diff --git "):
            header = True
        elif header and text.startswith("+++ "):
            path = text[len("+++ ") :]
        elif text.startswith("@@"):
            header = False
            m = _HUNK.search(text)
            if m:
                line = int(m[1])
        elif not header and text.startswith("+"):
            if ALLOW_SECRET not in text:
                what = next((what for what, p in _SECRET_KINDS if p.search(text)), "")
                if what:
                    found.append(f"{path}:{line}: {what}")
            line += 1
    return found
