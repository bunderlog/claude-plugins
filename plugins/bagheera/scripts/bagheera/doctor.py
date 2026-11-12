"""doctor: the plugin's state in the repo it runs in, its problems first, each with what fixes it
(ADR doctor): the plugin running and the link its Status line runs, the Session review's
Proposals, and the Checks, with the last one that failed; what an earlier baloo left in the
clone, for the person to remove; and what the repo lacks of being set up, which /bagheera:setup
adds (PRD setup); the deny rules the person's own settings lack (PRD deny); and the machine's
projects that need attention and the sessions waiting, which aren't its problems (PRD visibility). It changes nothing but what the
plugin's data folder keeps of them."""

from __future__ import annotations

import io
import json
import os
import time
from typing import List, TextIO

from bagheera import (
    attention, binlink, checks, deny, failure, hook, names, repo, review, settings, setup, version,
)


def run(stdout: TextIO, stderr: TextIO) -> int:
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{names.PLUGIN}: {e}\n")
        return 1
    root = repo.root(dir)
    problems: List[str] = []
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    w = io.StringIO()

    w.write(f"\nPlugin:\n  running\t{binlink.PLUGIN} ({version.read()})\n")
    newer = version.newer_installed(root) if root else ""
    if newer:
        problems.append(
            f"this session runs {names.PLUGIN} {version.read()}, but {newer} is installed for this "
            "project: restart Claude Code to run it"
        )
    link = ""
    if not data:
        problems.append(
            "CLAUDE_PLUGIN_DATA is not set, so the link the Status line runs can't be checked: run "
            "doctor as the doctor skill does"
        )
    else:
        link = os.path.join(data, names.PLUGIN)
        if not os.path.exists(link):
            w.write(f"  link\t{link}, missing\n")
            problems.append(
                f"{link} is missing, so the Status line runs nothing: the next session start "
                "points it at this plugin"
            )
        else:
            target = os.path.realpath(link)
            w.write(f"  link\t{link} -> {target}\n")
            if target != binlink.PLUGIN:
                problems.append(
                    f"{link} points at {target}, not at this plugin, so the Status line runs "
                    "that one: the next session start points it here"
                )

    try:
        rules = deny.missing()
        if rules:
            problems.append(
                f"{deny.user_file()} lacks {len(rules)} of {names.PLUGIN}'s deny rules: add to its "
                f"permissions.deny {json.dumps(rules)}"
            )
    except (OSError, ValueError) as e:
        problems.append(f"{e}: fix it so Claude Code reads its deny rules")

    if root and os.path.lexists(os.path.join(root, names.OLD_CONFIG)):
        problems.append(
            f"{os.path.join(root, names.OLD_CONFIG)} is no longer read: baloo has no settings of its "
            "own, so remove it"
        )

    if root:
        problems += _left_in_local(dir)
        if not setup.started(root):
            problems.append(f"{root} isn't set up for bunderlog's plugins: {names.SETUP_SKILL} "
                            "sets it up")
        else:
            for item in setup.missing(root):
                problems.append(f"{item} is missing: {names.SETUP_SKILL} adds it")

    if root:
        waiting = mismatches = 0
        for it in review.items(root, data):
            if it.mismatch:
                mismatches += 1
                problems.append(
                    f"{names.PROPOSALS}{it.review}.md, {it.id}: {it.mismatch}: fix the file, or "
                    "log the decision when the next session asks"
                )
            elif it.pending:
                waiting += 1
        failed, cost = review.week(root, data)
        w.write(
            f"\nSession review:\n  running\t{_bool(review.running(root, data))}\n"
            f"  proposals waiting\t{waiting}\n  mismatches\t{mismatches}\n"
            f"  failed this week\t{failed}\n  cost this week\t${cost:.2f}\n"
        )

    failed = failure.problem(data) if data else None
    if failed:
        problems.append(failed)
    w.write("\nChecks in Claude Code's hooks, always on:\n")
    for name in sorted(checks.HOOK_CHECKS):
        w.write(f"  {name}\ton\n")

    _machine(w, data)

    stdout.write(f"{names.PLUGIN} {version.read()} doctor in {dir}\n\n")
    if not problems:
        stdout.write("No problems.\n")
    else:
        stdout.write("Problems:\n")
        for p in problems:
            stdout.write(f"- {hook.one_line(p)}\n")
    stdout.write(_columns(w.getvalue()))
    return 1 if problems else 0


def _machine(w: io.StringIO, data: str) -> None:
    """Writes the machine's projects that need attention, each thing a line with what to do, the
    sessions waiting, and how many projects need nothing and how many aren't set up."""
    found = attention.check(data, repo.own_folder(), time.time())
    w.write(f"\nProjects on this machine, from the Transcripts of the last {attention.DAYS} days:\n")
    if not found.projects and not found.waits:
        w.write("  none found\n")
        return
    for wait in found.waits:
        since = time.strftime("%Y-%m-%d %H:%M", time.localtime(wait.since))
        w.write(f"  {wait.root or 'a folder outside any repo'}: a session waits for you since "
                f"{since}: switch to it\n")
    for p in found.projects:
        if p.needs:
            w.write(f"  {p.root}:\n")
            for n in p.needs:
                w.write(f"    - {n.what}: {n.fix}\n")
    quiet = len([p for p in found.projects if not p.needs])
    w.write(f"  need nothing\t{quiet}\n")
    w.write(f"  not set up\t{len([p for p in found.projects if not p.set_up])}\n")


def _left_in_local(dir: str) -> List[str]:
    """The Output style and the Status line an earlier Release wrote into the clone's
    settings.local.json, which the plugin no longer sets (PRD no-config), for the person to
    remove."""
    path = settings.files(dir)[settings.LOCAL]
    try:
        local = settings.read_all({settings.LOCAL: path})[settings.LOCAL]
    except (OSError, ValueError):
        return []
    found = []
    keys = setup.baloo_local(local)
    if "statusLine" in keys:
        found.append(f"{path} has the statusLine an earlier baloo wrote: remove it, and set "
                     "your own in ~/.claude/settings.json")
    if "outputStyle" in keys:
        found.append(f"{path} has the outputStyle an earlier baloo picked: remove it, and "
                     "pick your own in ~/.claude/settings.json")
    return found


def _columns(text: str) -> str:
    """`text` with the first cell of each run of lines holding a tab padded to one width, two
    spaces past the widest, as Go's tabwriter aligns doctor's tables."""
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        if "\t" not in lines[i]:
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and "\t" in lines[j]:
            j += 1
        cells = [line.split("\t", 1) for line in lines[i:j]]
        width = max(len(first) for first, _ in cells) + 2
        out.extend(first.ljust(width) + rest for first, rest in cells)
        i = j
    return "\n".join(out)


def _bool(b: bool) -> str:
    return "true" if b else "false"


def _or_none(s: str) -> str:
    """`s`, or "none" where it is empty."""
    return s or "none"
