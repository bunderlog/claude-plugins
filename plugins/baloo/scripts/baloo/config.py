"""Reads a repo's Config, .claude/baloo.yml, and writes a new one (ADR config). A Config that is
wrong in part still applies in part: each wrong setting is a problem, one line for Claude, and its
default applies, so a mistake never stops a Check."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from baloo import checks, guidelines, names, settings, statusline, yaml
from baloo.checks import CommitRules
from baloo.yaml import Node


@dataclass
class Config:
    """A repo's settings. What a new key needs is in ADR config's Consequences; a Check also needs
    its name in checks.HOOK_CHECKS, or a Git hook's Check its entry in the checks package's
    registry."""

    # The root of the repo whose Config this is, or "" where the repo has none (see load).
    root: str = ""
    # The plugin's Output style that session start picks where Claude Code's settings pick none
    # (ADR output-styles), or "" for none.
    output_style: str = ""
    # Whether session start sets the plugin's Status line or takes it out (ADR status-line), or
    # None where the Config doesn't say, and the line is left as it is.
    status_line: Optional[bool] = None
    # The Status line's bars, their order and thresholds, or None where the Config sets none and
    # statusline.default() applies.
    status_layout: Optional[statusline.Layout] = None
    # Whether a Session review starts when a session ends (ADR session-review).
    session_review: bool = False
    # The command run on each file Claude edits, or "" where it is off (ADR format-on-edit).
    format_on_edit: str = ""
    # The project's own commands the Git hooks run after their Checks, by Git hook (ADR
    # git-hooks).
    git_hook_commands: Dict[str, str] = field(default_factory=dict)
    # The Guidelines turned on, by name (ADR guidelines).
    guidelines: Dict[str, bool] = field(default_factory=dict)
    # The Checks the Config turns on or off, by name; see check_on for one it doesn't.
    checks: Dict[str, bool] = field(default_factory=dict)
    # conventional-commits' settings.
    commit_rules: CommitRules = field(default_factory=CommitRules)
    # no-large-files' limit, in KB, or 0 for its default.
    max_file_kb: int = 0
    # The settings of _REMOVED, one line each, for doctor to name (see _REMOVED).
    removed: List[str] = field(default_factory=list)

    def check_on(self, name: str) -> bool:
        """Whether the Check `name` is on: as the Config says, and else on for a Check a Hook runs,
        off for a Git hook's (ADR checks)."""
        if name in self.checks:
            return self.checks[name]
        return name in checks.HOOK_CHECKS

    def git_hook_runs(self, name: str) -> bool:
        """Whether a Git hook runs `name`: a Check the Config turns on, or the command
        `git-hook-commands.<hook>` it sets."""
        prefix = names.GIT_HOOK_COMMANDS + "."
        if name.startswith(prefix):
            return self.git_hook_commands.get(name[len(prefix) :], "") != ""
        return self.check_on(name)


# The plugin's Output styles, the files in its output-styles/.
OUTPUT_STYLES = ["short-replies"]

# The settings earlier Releases had and this one dropped (ADR measurement): a Config that still has
# one works as without it, and only doctor names it, for the user to delete.
_REMOVED = ["stop-check", "claude-hooks.no-destructive-commands"]


def _removed_at(line: int, name: str) -> str:
    """The line doctor shows for the removed setting `name` at line `line`."""
    return _at(line, name + " is no longer a setting and is ignored: delete it")


def _at(line: int, text: str) -> str:
    """The problem `text` at line `line` of the Config."""
    return f"{names.CONFIG} line {line}: {text}"


def _wrong(line: int, name: str, why: str) -> str:
    """The problem of the setting `name` at line `line`, whose value is wrong as `why` says, so its
    default applies."""
    return _at(line, name + ": " + why + "; its default applies")


def _is_false(value: Node) -> bool:
    return value.tag == "bool" and value.value is False


def _strings(value: Node) -> Optional[List[str]]:
    """The list `value` as strings, or None where it isn't a list of scalars."""
    if value.tag != "seq" or any(item.tag in ("map", "seq") for item in value.items):
        return None
    return ["" if item.tag == "null" else item.text for item in value.items]


def _output_style(c: Config, key: Node, value: Node) -> List[str]:
    if _is_false(value):
        c.output_style = ""
        return []
    if value.tag != "str" or value.text not in OUTPUT_STYLES:
        why = "is not false or one of " + ", ".join(OUTPUT_STYLES)
        return [_wrong(key.line, key.text, why)]
    c.output_style = value.text
    return []


def _status_line(c: Config, key: Node, value: Node) -> List[str]:
    if value.tag == "map":
        c.status_line = True
        c.status_layout, problems = _status_layout(key.text, value)
        return problems
    if value.tag != "bool":
        why = ": is not true, false or its bars and thresholds; the Status line is left as it is"
        return [_at(key.line, key.text + why)]
    c.status_line = value.value
    return []


def _session_review(c: Config, key: Node, value: Node) -> List[str]:
    if value.tag != "bool":
        return [_wrong(key.line, key.text, "is not true or false")]
    c.session_review = value.value
    return []


def _format_on_edit(c: Config, key: Node, value: Node) -> List[str]:
    cmd, problems = _command_at(key.line, key.text, value)
    if cmd:
        c.format_on_edit = cmd
    return problems


def _git_hook_commands(c: Config, key: Node, value: Node) -> List[str]:
    if value.tag == "null":
        return []
    if value.tag != "map":
        return [_wrong(key.line, key.text, "is not a map of Git hooks to commands")]
    problems: List[str] = []
    for hook, cmd in value.pairs:
        entry = key.text + "." + hook.text
        if hook.text not in checks.GIT_HOOKS:
            problems.append(_at(hook.line, entry + " is not a Git hook of the plugin's; ignored"))
            continue
        got, wrong = _command_at(hook.line, entry, cmd)
        problems += wrong
        if got:
            c.git_hook_commands[hook.text] = got
    return problems


def _guidelines(c: Config, key: Node, value: Node) -> List[str]:
    if value.tag == "null":
        return []
    if value.tag != "map":
        return [_wrong(key.line, key.text, "is not a map of guidelines to true or false")]
    c.guidelines = {}
    problems: List[str] = []
    for name, on in value.pairs:
        entry = key.text + "." + name.text
        if name.text not in guidelines.names():
            problems.append(_at(name.line, entry + " is not a guideline; ignored"))
            continue
        if on.tag != "bool":
            problems.append(_wrong(name.line, entry, "is not true or false"))
            continue
        c.guidelines[name.text] = on.value
    return problems


def _check_keys(group: List[str]) -> Callable[[Config, Node, Node], List[str]]:
    """Decodes a group of Checks' keys, those of the Checks `group`, into a Config."""

    def decode(c: Config, key: Node, value: Node) -> List[str]:
        if value.tag == "null":
            return []
        if value.tag != "map":
            return [_wrong(key.line, key.text, "is not a map of checks to true or false")]
        problems: List[str] = []
        for name, on in value.pairs:
            entry = key.text + "." + name.text
            if entry in _REMOVED:
                c.removed.append(_removed_at(name.line, entry))
                continue
            if name.text not in group:
                problems.append(_at(name.line, entry + " is not a check; ignored"))
                continue
            settings_of = _CHECK_SETTINGS.get(name.text)
            if settings_of is not None and on.tag == "map":
                c.checks[name.text] = True
                problems += settings_of(c, entry, on)
                continue
            if on.tag != "bool":
                problems.append(_wrong(name.line, entry, "is not true or false"))
                continue
            c.checks[name.text] = on.value
        return problems

    return decode


def _no_large_files(c: Config, entry: str, value: Node) -> List[str]:
    problems: List[str] = []
    for key, v in value.pairs:
        setting = entry + "." + key.text
        if key.text != "max-size":
            problems.append(_at(key.line, setting + " is not a setting of no-large-files; ignored"))
            continue
        if v.tag != "int" or v.value < 1:
            problems.append(_wrong(key.line, setting, "is not a size of 1 KB or more"))
            continue
        c.max_file_kb = v.value
    return problems


def _commit_rules(c: Config, entry: str, value: Node) -> List[str]:
    """Decodes conventional-commits' settings, the map `value` at `entry`, into the Config's
    commit_rules, and returns what is wrong with them; each wrong one keeps its default."""
    rules = c.commit_rules
    problems: List[str] = []
    for key, v in value.pairs:
        setting = entry + "." + key.text
        if key.text == "types":
            types = _strings(v)
            if v.tag == "str" and v.text == "any":
                rules.any_type = True
            elif types is not None:
                rules.types = types
            else:
                problems.append(_wrong(key.line, setting, "is not a list of types or any"))
        elif key.text == "max-length":
            if v.tag != "int" or v.value < 0:
                problems.append(_wrong(key.line, setting, "is not a length of 0 or more"))
                continue
            rules.max_length = v.value
        else:
            why = " is not a setting of conventional-commits; ignored"
            problems.append(_at(key.line, setting + why))
    return problems


# The settings a Check takes instead of true, the map `value` at `entry`, decoded into a Config,
# which turns it on; each returns what is wrong with them, and each wrong one keeps its default.
_CHECK_SETTINGS: Dict[str, Callable[[Config, str, Node], List[str]]] = {
    "conventional-commits": _commit_rules,
    "no-large-files": _no_large_files,
}


def _status_layout(entry: str, value: Node) -> Tuple[statusline.Layout, List[str]]:
    """Decodes the Status line's settings, the map `value` at `entry`, and returns what is wrong
    with them; each wrong one keeps its default, a wrong bar in the list is left out."""
    layout = statusline.default()
    bars = ", ".join(statusline.BARS)
    problems: List[str] = []
    for key, v in value.pairs:
        setting = entry + "." + key.text
        if key.text == "bars":
            got = _strings(v)
            if got is None:
                problems.append(_wrong(key.line, setting, "is not a list of " + bars))
                continue
            layout.bars = []
            for item, name in zip(v.items, got):
                if name not in statusline.BARS:
                    why = ": " + name + " is not one of " + bars + "; ignored"
                    problems.append(_at(item.line, setting + why))
                elif name in layout.bars:
                    problems.append(_at(item.line, setting + ": " + name + " is there twice; ignored"))
                else:
                    layout.bars.append(name)
        elif key.text == "thresholds":
            if v.tag != "map":
                problems.append(_wrong(key.line, setting, "is not a map of bars to thresholds"))
                continue
            for name, t in v.pairs:
                bar = setting + "." + name.text
                if name.text not in layout.thresholds:
                    problems.append(_at(name.line, bar + " is not one of " + bars + "; ignored"))
                    continue
                got_t, why = _thresholds(layout.thresholds[name.text], t)
                if why:
                    problems.append(_wrong(name.line, bar, why))
                    continue
                if not statusline.ordered(name.text, got_t):
                    problems.append(_wrong(name.line, bar, "turns red before yellow"))
                    continue
                layout.thresholds[name.text] = got_t
        else:
            problems.append(_at(key.line, setting + " is not a setting of status-line; ignored"))
    return layout, problems


def _thresholds(t: statusline.Thresholds, value: Node) -> Tuple[statusline.Thresholds, str]:
    """A bar's thresholds `t` with those the map `value` sets, and what is wrong with them, or
    ""."""
    why = "is not { yellow: <percent>, red: <percent> }"
    if value.tag != "map":
        return t, why
    yellow, red = t.yellow, t.red
    for key, v in value.pairs:
        if v.tag != "int" or not 0 <= v.value <= 100:
            return t, why
        if key.text == "yellow":
            yellow = v.value
        elif key.text == "red":
            red = v.value
        else:
            return t, why
    return statusline.Thresholds(yellow=yellow, red=red), ""


def _command_at(line: int, name: str, value: Node) -> Tuple[str, List[str]]:
    """The command `value` names for the setting `name` at line `line`, or "" where it is false
    or wrong, with what is wrong with it."""
    if _is_false(value):
        return "", []
    if value.tag != "str" or not value.text.strip():
        return "", [_wrong(line, name, "is not a command or false")]
    return value.text, []


# Decodes each setting's value into a Config, and returns what is wrong with it, a problem per
# line (see _at); a key that isn't here is not a setting.
_KEYS: Dict[str, Callable[[Config, Node, Node], List[str]]] = {
    "output-style": _output_style,
    "status-line": _status_line,
    "session-review": _session_review,
    "format-on-edit": _format_on_edit,
    names.GIT_HOOK_COMMANDS: _git_hook_commands,
    "claude-hooks": _check_keys(checks.HOOK_CHECKS),
    "git-hooks": _check_keys(checks.GIT_HOOK_CHECKS),
    "guidelines": _guidelines,
}


def _new_config(fit: List[str]) -> str:
    """A new Config, with the Guidelines `fit` on: it names the schema for editors, and says in
    plain words how the settings work, for someone who has read neither the schema nor the
    README. The keys of each section are sorted, so one is found by its name."""
    listed = "".join(
        f"  {name}: {'true' if name in fit else 'false'}\n" for name in sorted(guidelines.names())
    )
    hook_list = "".join(f"  {name}: true\n" for name in sorted(checks.HOOK_CHECKS))
    git_hook_list = "".join(f"  {name}: true\n" for name in sorted(checks.GIT_HOOK_CHECKS))
    return (
        "# yaml-language-server: $schema=" + names.SCHEMA + """
#
# baloo's settings for this repo. Each Check and each Guideline turns on or off with a key of its
# own here. A wrong setting is reported at session start, and its default applies.

# The Output style for Claude's replies, picked at session start in the settings file that
# enables the plugin (the project's .claude/settings.local.json for the user's settings), where no
# settings file of Claude Code's picks one; false picks none.
output-style: short-replies

# The plugin's Status line, set at session start in .claude/settings.local.json, where no
# settings file of Claude Code's but the user's own sets one; false takes it out. Instead of
# true it also takes its bars, in the order shown, and the percentages at which each turns yellow
# and red, such as { bars: [context, 5h], thresholds: { context: { yellow: 30, red: 50 } } };
# cache's are of the cache's lifetime left, so red is below yellow.
status-line: true

# The Session review: when a session ends, a separate Claude session proposes, in .about/proposals/,
# changes to .about/ for what the conversation settled or left open but nobody wrote down; a
# later session shows you each, to accept, reject or defer. It never edits .about/ or commits.
session-review: true

# Format on edit: after each of Claude's edits to a file in the repo, it runs this command in the
# repo's root with the file's path at the end, and says nothing of how it went. Off without it, or
# with false.
# format-on-edit: npx prettier --write

# The project's own commands, by Git hook (pre-commit, commit-msg, pre-push), that the plugin's Git
# hook runs with sh after its Checks pass, with git's arguments as $1 and, for pre-push, the pushed
# refs on stdin; the commit or push fails when the command does. Off without it, or with false.
# git-hook-commands:
#   pre-commit: mise run test

# Guidelines, the plugin's working rules: each one on is named to Claude at session start, for
# Claude to read when a task calls for it, but typescript, vue and testing, which Claude is given
# whole the first time it reads or edits a file of their subject in a session. A stack's is on
# where the repo had that stack when this file was made, ci where it had a CI's config, and
# dependencies where it had a package manager's manifest.
guidelines:
"""
        + listed
        + """
# Checks, each on with true and off with false.
#
# Checks in Claude Code's hooks deny a tool call of Claude's that would bypass the Git hooks or show
# a secret. They are on without their key too.
claude-hooks:
"""
        + hook_list
        + """
# Checks in Git hooks check every commit or push, yours or Claude's. The Git hooks are written
# where at least one of their Checks is on. conventional-commits also takes its settings instead
# of true, such as { types: [feat, fix], max-length: 72 }; types: any takes any type,
# max-length: 0 any length. no-large-files takes { max-size: 5000 }, in KB; 1024 without it.
git-hooks:
"""
        + git_hook_list
    )


def _repo(folder: str) -> Tuple[str, bool]:
    """The root of the repo `folder` is in, where its Config is: the nearest folder up from
    `folder` that holds a .git, or `folder` itself outside a repo, with whether `folder` is in a
    repo at all."""
    d = folder
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d, True
        parent = os.path.dirname(d)
        if parent == d:
            return folder, False
        d = parent


def load(folder: str) -> Tuple[Config, str, List[str]]:
    """Reads the Config of the repo `folder` is in, with its problems, after creating it when the
    repo has none (see _create); it also returns the path of one it created. Outside a repo, when
    the repo is the home folder itself (a dotfiles repo), or when it is in Claude Code's own
    folder, it neither reads nor writes one, and every setting has its default: the home folder's
    .claude/ is Claude Code's own settings, not a repo's, and what is inside it is Claude Code's to
    write."""
    root, in_repo = _repo(folder)
    if not in_repo or _claude_codes(root):
        return Config(), "", []
    problems: List[str] = []
    created = ""
    try:
        created = _create(root)
    except OSError as e:
        if e.filename:  # it names the path already
            problems.append(f"could not create {e.filename}: {_why(e)}")
        else:
            problems.append(f"could not create {names.CONFIG}: {_why(e)}")
    c, more = _read(root)
    c.root = root
    return c, created, problems + more


def read(folder: str) -> Config:
    """Reads the Config of the repo `folder` is in, as load does, but never creates one, and
    leaves its problems for session start to report."""
    root, in_repo = _repo(folder)
    if not in_repo or _claude_codes(root):
        return Config()
    c, _ = _read(root)
    c.root = root
    return c


def inspect(folder: str) -> Tuple[Config, str, List[str]]:
    """Reads the Config of the repo `folder` is in, as read does, with its problems, and returns
    its path, or "" where the repo has none or no Config is read."""
    root, in_repo = _repo(folder)
    if not in_repo or _claude_codes(root):
        return Config(), "", []
    c, problems = _read(root)
    c.root = root
    path = os.path.join(root, names.CONFIG)
    return c, path if os.path.exists(path) else "", problems


def _why(e: OSError) -> str:
    """`e`'s reason as Go words it, such as `permission denied`."""
    why = e.strerror or str(e)
    return why[:1].lower() + why[1:]


def _read(root: str) -> Tuple[Config, List[str]]:
    path = os.path.join(root, names.CONFIG)
    try:
        with open(path, encoding="utf-8") as f:
            data = f.read()
    except FileNotFoundError:
        return Config(), []
    except OSError as e:
        return Config(), [f"{names.CONFIG}: open {path}: {_why(e)}; none of it applies"]
    except UnicodeDecodeError as e:
        return Config(), [f"{names.CONFIG}: {e}; none of it applies"]
    return parse(data)


def parse(data: str) -> Tuple[Config, List[str]]:
    """The Config the text `data` sets, with its problems."""
    c = Config()
    try:
        top = yaml.parse(data)
    except yaml.Error as e:
        return c, [f"{names.CONFIG}: {e}; none of it applies"]
    if top is None:  # empty, or only comments
        return c, []
    if top.tag != "map":
        return c, [f"{names.CONFIG} line {top.line}: not a map of settings; none of it applies"]
    problems: List[str] = []
    for key, value in top.pairs:
        if key.text in _REMOVED:
            c.removed.append(_removed_at(key.line, key.text))
            continue
        set_ = _KEYS.get(key.text)
        if set_ is None:
            problems.append(_at(key.line, key.text + " is not a setting; ignored"))
            continue
        problems += set_(c, key, value)
    return c, problems


def _create(root: str) -> str:
    """Writes a new Config, every Check on and the Guidelines that fit the repo, at the repo root
    `root` when it has none, and returns its path; with a Config there already, it writes nothing
    and returns "". The repo is looked through for its stacks before the file is made, so it never
    sits empty for longer than one write."""
    path = os.path.join(root, names.CONFIG)
    if os.path.lexists(path):
        return ""
    text = _new_config(guidelines.fitting(root))
    os.makedirs(os.path.dirname(path), mode=0o755, exist_ok=True)
    try:
        f = open(path, "x", encoding="utf-8")
    except FileExistsError:
        return ""
    try:
        with f:
            f.write(text)
    except BaseException:
        # Half a Config would pass for the user's own from then on, and never be written again.
        try:
            os.remove(path)
        except OSError:
            pass
        raise
    return path


def _claude_codes(root: str) -> bool:
    """Whether the repo root `root` is the home folder, or Claude Code's own folder,
    CLAUDE_CONFIG_DIR or ~/.claude, or inside it, such as a marketplace it cloned."""
    home = os.environ.get("HOME", "")
    if home and _resolve(root) == _resolve(home):
        return True
    own = settings.own()
    if not own:
        return False
    rel = os.path.relpath(_resolve(root), _resolve(own))
    return rel != ".." and not rel.startswith(".." + os.sep)


def _resolve(p: str) -> str:
    """The path `p` with its links followed, so two spellings of one folder compare equal."""
    return os.path.realpath(p)
