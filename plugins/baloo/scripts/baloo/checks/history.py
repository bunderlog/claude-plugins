"""The Check linear-history."""

from __future__ import annotations

from typing import List

from baloo.checks.git import Error, git


def linear_history(dir: str, pushed: str) -> List[str]:
    """The Check baloo:linear-history (pre-push): `<ref> <commit>` for each merge commit the push
    `pushed` sends from the repo `dir`, given as git gives pre-push its stdin, a
    `<local ref> <local sha> <remote ref> <remote sha>` line per ref. A ref new to the remote, or
    whose remote commit isn't here, is checked against every remote-tracking branch. Any other is
    checked against its remote commit and each remote's default branch, which has the merges a
    branch rebased onto it brings along; that remote's tracking ref of the branch pushed to doesn't
    count, as the push replaces it. A deletion sends no commits. It raises an Error where git
    fails, such as on a commit not in the repo."""
    defaults = git(dir, "for-each-ref", "--format=%(refname) %(symref)", "refs/remotes/*/HEAD")
    found = []
    for line in pushed.split("\n"):
        fields = line.split()
        if len(fields) < 4 or not fields[1].strip("0"):
            continue
        ref, local, to, remote = fields[:4]
        sends = [local, "--not", "--remotes"]
        if remote.strip("0"):
            try:
                git(dir, "cat-file", "-e", remote + "^{commit}")
            except Error:
                pass
            else:
                sends = [local, "--not", remote]
                for default in defaults.strip().split("\n"):
                    head, _, branch = default.partition(" ")
                    pushed_to = head.removesuffix("HEAD") + to.removeprefix("refs/heads/")
                    if branch and branch != pushed_to:
                        sends.append(branch)
        merges = git(dir, "rev-list", "--merges", *sends)
        found += [f"{ref} {commit[:12]}" for commit in merges.split()]
    return found
