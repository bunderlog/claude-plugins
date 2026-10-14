"""Makes a Release of the baloo plugin (ADR releases). It is not part of the plugin, so a change to
it needs no Release. Run it from anywhere in the repo:

    python3 src/release/release.py    make a Release from the commits since the last one
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "plugins",
        "baloo",
        "scripts",
    ),
)

from baloo import names  # noqa: E402


class Error(Exception):
    """Why a Release wasn't made, or was made only in part."""


@dataclass
class Commit:
    """One commit since the last Release: its short sha and full message."""

    sha: str
    message: str


# The paths whose change needs a Release, and whose commits alone count for its version and
# CHANGELOG: the plugin, but not what users don't get from a Release: the schema, which editors
# read from main. Its tests are in tests/, outside it.
CHANGES = [names.PLUGIN_DIR, ":!" + names.PLUGIN_DIR + "/schema.json"]

CHANGELOG_HEADER = "# Changelog\n\nThe " + names.PLUGIN + " plugin's Releases, newest first.\n"

# A Conventional Commits subject: type, optional scope, optional `!`, description.
_SUBJECT = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?: (.+)$", re.A)

_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.M)


def _parts(c: Commit) -> List[str]:
    first, _, body = c.message.partition("\n")
    m = _SUBJECT.match(first)
    parts = [m.group(0)] + [g or "" for g in m.groups()] if m else [""] * 5
    if _BREAKING_FOOTER.search(body):
        parts[3] = "!"
    return parts


def _breaking(c: Commit) -> bool:
    return _parts(c)[3] == "!"


def _is_feature(c: Commit) -> bool:
    return not _breaking(c) and _parts(c)[1] == "feat"


def _is_fix(c: Commit) -> bool:
    return not _breaking(c) and _parts(c)[1] == "fix"


def next_version(version: str, commits: List[Commit], changed: bool) -> str:
    """The version after `version` for these commits, or "" when the plugin didn't change. Below
    1.0 a breaking change raises the minor, as a feat does; from 1.0 it raises the major; anything
    else raises the patch."""
    if not changed:
        return ""
    fields = version.split(".")
    if len(fields) != 3 or not all(re.fullmatch(r"[+-]?[0-9]+", f) for f in fields):
        raise Error(f'version "{version}" is not major.minor.patch')
    v = [int(f) for f in fields]
    breaking = any(_breaking(c) for c in commits)
    if breaking and v[0] > 0:
        v = [v[0] + 1, 0, 0]
    elif breaking or any(_is_feature(c) for c in commits):
        v = [v[0], v[1] + 1, 0]
    else:
        v[2] += 1
    return "%d.%d.%d" % tuple(v)


def section(version: str, date: str, commits: List[Commit]) -> str:
    """The CHANGELOG section for `version`: its breaking changes, features and fixes, oldest
    first."""
    body = ""
    for title, keep in (
        ("Breaking changes", _breaking),
        ("Features", _is_feature),
        ("Fixes", _is_fix),
    ):
        listed = [c for c in commits if keep(c)]
        if not listed:
            continue
        if body:
            body += "\n"
        body += f"### {title}\n\n"
        for c in listed:
            m = _parts(c)
            scope = m[2] + ": " if m[2] else ""
            body += f"- {scope}{m[4]} ({c.sha})\n"
    if not body:
        body = "No feature changes or fixes.\n"
    return f"## {version} — {date}\n\n{body}"


# The line of the README's CI recipe that names the Release it pins.
_PINNED = re.compile(r"^version=\S+$", re.M | re.A)


def pin(readme: str, version: str) -> str:
    """The README `readme` with its CI recipe pinning `version`; an Error unless it has exactly
    one line to pin."""
    n = len(_PINNED.findall(readme))
    if n != 1:
        raise Error(f"README.md has {n} lines `version=<version>` for its CI recipe; want one")
    return _PINNED.sub(lambda _: "version=" + version, readme)


def _git(root: str, *args: str) -> str:
    """What git, run in `root` with `args`, prints, trimmed; an Error when it fails."""
    p = subprocess.run(
        ["git", "-C", root, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if p.returncode != 0:
        raise Error(f"git {args[0]}: exit status {p.returncode}: {p.stderr.strip()}")
    return p.stdout.strip()


def version(root: str) -> str:
    """The plugin's version, in its manifest in the repo at `root`."""
    path = os.path.join(root, names.MANIFEST)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise Error(f"{names.MANIFEST}: {e.strerror or e}") from e
    m = re.search(r'"version":\s*"([^"]*)"', text)
    if not m or not m.group(1):
        raise Error(f"{names.MANIFEST} has no version")
    return m.group(1)


def _read(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except FileNotFoundError:
        return None


def release(root: str, today: str) -> str:
    """Makes a Release in the repo at `root` from the commits since the last `v*` tag: it writes
    the next version to the manifest and the README's CI recipe and a section to CHANGELOG.md,
    commits these and tags the commit, signed, for `mise run release` to push with main. It
    returns the version."""
    try:
        clean = _git(root, "status", "--porcelain") == ""
    except Error:
        clean = False
    if not clean:
        raise Error("commit or stash your changes first")
    current = version(root)
    since = "HEAD"
    changed = True
    try:
        tag = _git(root, "describe", "--tags", "--abbrev=0", "--match", "v*")
    except Error:
        tag = ""
    if tag:
        if tag[1:] != current:
            raise Error(f"the last tag is {tag}, but {names.MANIFEST} says {current}")
        since = tag + "..HEAD"
        changed = _git(root, "diff", "--name-only", tag, "HEAD", "--", *CHANGES) != ""
    log = _git(root, "log", "--reverse", "--format=%h%x00%B%x1e", since, "--", *CHANGES)
    commits = []
    for entry in log.split("\x1e"):
        sha, _, message = entry.strip().partition("\x00")
        if sha:
            commits.append(Commit(sha, message.strip()))
    new = next_version(current, commits, changed)
    if not new:
        raise Error(f"nothing to release: {' '.join(CHANGES)} is unchanged since v{current}")

    # Every file is read and checked before any is written, so a failure leaves none half done.
    readme = os.path.join(root, "README.md")
    text = _read(readme)
    if text is None:
        raise Error(f"open {readme}: no such file or directory")
    pinned = pin(text, new)
    manifest = os.path.join(root, names.MANIFEST)
    text = _read(manifest)
    if text is None:
        raise Error(f"open {manifest}: no such file or directory")
    bumped = re.sub(r'("version":\s*")[^"]*"', lambda m: m.group(1) + new + '"', text)
    file = os.path.join(root, "CHANGELOG.md")
    old = _read(file)
    if old is None:
        old = CHANGELOG_HEADER
    entry = "\n" + section(new, today, commits)
    at = old.find("\n## ")
    changelog = old[:at] + entry + old[at:] if at >= 0 else old + entry
    for path, out in ((manifest, bumped), (file, changelog), (readme, pinned)):
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(out)

    _git(root, "add", names.MANIFEST, "CHANGELOG.md", "README.md")
    msg = "chore(release): " + new
    push = f"git push --atomic origin main v{new}"
    if subprocess.run(["git", "-C", root, "commit", "-q", "-m", msg], stdout=sys.stderr).returncode:
        raise Error(
            "the release commit failed: fix what failed, then "
            f'`git commit -m "{msg}" && git tag -s v{new} -m v{new} && {push}`'
        )
    # Signed whatever tag.gpgSign says, as ADR releases has it: -a alone would make an unsigned
    # tag.
    p = subprocess.run(
        ["git", "-C", root, "tag", "-s", "v" + new, "-m", "v" + new],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if p.returncode:
        raise Error(
            f"the release tag failed: fix what failed, then `git tag -s v{new} -m v{new} && "
            f"{push}`: {p.stdout}"
        )
    return new


def main(args: List[str]) -> int:
    if args:
        print("release: usage: python3 src/release/release.py", file=sys.stderr)
        return 1
    try:
        root = _git(os.getcwd(), "rev-parse", "--show-toplevel")
    except Error as e:
        print(f"release: not in the repo: {e}", file=sys.stderr)
        return 1
    try:
        new = release(root, date.today().isoformat())
    except (Error, OSError) as e:
        print(f"release: {e}", file=sys.stderr)
        return 1
    print(f"released {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
