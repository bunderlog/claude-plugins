"""doctor: the plugin's state in the repo it runs in, its problems first, each with what fixes it
(ADR doctor): the plugin running and the link the Git hooks run, the Config's settings, the Session
review's Proposals, each Check on or off and why, the Git hooks and the Guidelines. It changes
nothing, for session start does the fixing, and fails when it finds a problem."""

from __future__ import annotations

import io
import os
from typing import List, TextIO

from baloo import binlink, checks, config, githooks, guidelines, hook, names, review, version


def run(stdout: TextIO, stderr: TextIO) -> int:
    try:
        dir = hook.project()
    except OSError as e:
        stderr.write(f"{names.PLUGIN}: {e}\n")
        return 1
    c, path, problems = config.inspect(dir)
    problems = problems + c.removed
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    w = io.StringIO()

    w.write(f"\nPlugin:\n  running\t{binlink.PLUGIN} ({version.read()})\n")
    link = ""
    if not data:
        problems.append(
            "CLAUDE_PLUGIN_DATA is not set, so the link the Git hooks run can't be checked: run "
            "doctor as the doctor skill does"
        )
    else:
        link = os.path.join(data, names.PLUGIN)
        if not os.path.exists(link):
            w.write(f"  link\t{link}, missing\n")
            problems.append(
                f"{link} is missing, so the Git hooks and the Status line run nothing: the next "
                "session start points it at this plugin"
            )
        else:
            target = os.path.realpath(link)
            w.write(f"  link\t{link} -> {target}\n")
            if target != binlink.PLUGIN:
                problems.append(
                    f"{link} points at {target}, not at this plugin, so the Git hooks and the "
                    "Status line run that one: the next session start points it here"
                )

    if not c.root:
        w.write(
            "\nConfig: none, outside a repo or in Claude Code's own folder, so every setting has "
            "its default\n"
        )
    elif not path:
        w.write(
            f"\nConfig: none in {c.root}, so every setting has its default: the next session "
            f"start creates {names.CONFIG}\n"
        )
    else:
        w.write(f"\nConfig: {path}\n")
    status_line = "not set" if c.status_line is None else _bool(c.status_line)
    for key, value in [
        ("output-style", _or_none(c.output_style)),
        ("status-line", status_line),
        ("session-review", _bool(c.session_review)),
        ("format-on-edit", _or_none(c.format_on_edit)),
    ]:
        w.write(f"  {key}\t{value}\n")

    if c.root:
        waiting = mismatches = 0
        for it in review.items(c.root, data):
            if it.mismatch:
                mismatches += 1
                problems.append(
                    f"{names.PROPOSALS}{it.review}.md, {it.id}: {it.mismatch}: fix the file, or "
                    "log the decision when the next session asks"
                )
            elif it.pending:
                waiting += 1
        w.write(
            f"\nSession review:\n  running\t{_bool(review.running(c.root, data))}\n"
            f"  proposals waiting\t{waiting}\n  mismatches\t{mismatches}\n"
        )

    for title, group in [
        ("Checks in Claude Code's hooks (claude-hooks):", checks.HOOK_CHECKS),
        ("Checks in Git hooks (git-hooks):", checks.GIT_HOOK_CHECKS),
    ]:
        w.write(f"\n{title}\n")
        for name in sorted(group):
            state = "on" if c.check_on(name) else "off"
            if name not in c.checks:
                state += ", by default"
            w.write(f"  {name}\t{state}\n")

    if c.root:
        try:
            hooks_dir, husky, hooks = githooks.inspect(c.root, data, c.git_hook_runs)
        except (OSError, checks.Error) as e:
            problems.append(f"could not read the Git hooks: {e}")
        else:
            problems += git_hook_problems(hooks, link)
            via = ", run by husky 9" if husky else ""
            w.write(f"\nGit hooks in {hooks_dir}{via}:\n")
            for h in hooks:
                w.write(f"  {h.name}\t{h.state}")
                if h.runs:
                    w.write(": " + ", ".join(h.runs))
                w.write("\n")

    on = sorted(n for n in guidelines.names() if c.guidelines.get(n))
    off = sorted(n for n in guidelines.names() if not c.guidelines.get(n))
    w.write(
        f"\nGuidelines:\n  on\t{_or_none(', '.join(on))}\n  off\t{_or_none(', '.join(off))}\n"
    )

    stdout.write(f"{names.PLUGIN} {version.read()} doctor in {dir}\n\n")
    if not problems:
        stdout.write("No problems.\n")
    else:
        stdout.write("Problems:\n")
        for p in problems:
            stdout.write(f"- {hook.one_line(p)}\n")
    stdout.write(_columns(w.getvalue()))
    return 1 if problems else 0


def git_hook_problems(hooks: List[githooks.Hook], link: str) -> List[str]:
    """The problems of the Git hooks `hooks`, which the plugin runs through `link`, each with what
    fixes it."""
    problems = []
    for h in hooks:
        runs = ", ".join(h.runs)
        if h.state == githooks.MISSING:
            problems.append(
                f"{h.path} is missing, so {runs} don't run: the next session start writes it"
            )
        elif h.state == githooks.THEIRS:
            problems.append(
                f"{h.path} is not the plugin's Git hook, so {runs} don't run: move it out of the "
                f"way and start a session, or turn their keys in {names.CONFIG} off"
            )
        elif h.state == githooks.OUTDATED:
            if link and h.link != link:
                problems.append(
                    f"{h.path} runs {h.link}, not {link}: the next session start rewrites it"
                )
            else:
                problems.append(
                    f"{h.path} is not as this version writes it: the next session start rewrites "
                    "it"
                )
        elif h.state == githooks.LEFTOVER:
            problems.append(
                f"{h.path} is the plugin's, but {names.CONFIG} turns its checks and command off: "
                "the next session start takes it out"
            )
        if h.husky_outdated:
            problems.append(
                f".husky/{h.name} is not as session start keeps its line that runs the plugin's "
                "Git hook: the next session start fixes it, and the change is yours to commit"
            )
    return problems


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
