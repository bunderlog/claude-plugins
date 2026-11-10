"""Setting a repo up for bunderlog's plugins (PRD setup): what its working tree lacks of PRD
project-setup's list, which doctor names and session start tells of, and the run that adds it,
which the setup skill makes. A run writes only files in the repo and its clone's .git/hooks; it
makes no commit and changes no git config."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bagheera import names, settings, statusline

MARKETPLACE_SOURCE = {"source": "github", "repo": names.MARKETPLACE_REPO}
PLUGINS = [names.KNOWLEDGE + "@" + names.MARKETPLACE, names.BUILD + "@" + names.MARKETPLACE]
DENY = [
    "Read(**/.env)", "Read(**/.env.local)", "Read(**/.env.*.local)", "Read(**/.env.development)",
    "Read(**/.env.production)", "Read(**/.env.staging)", "Read(**/.env.test)", "Read(**/.envrc)",
    "Read(**/*.pem)", "Read(**/*.key)", "Read(**/id_rsa)", "Read(**/id_ed25519)",
    "Read(~/.ssh/id_*)", "Read(~/.aws/credentials)",
]
IGNORED = ["/.about/proposals/", "/.claude/worktrees/"]
HOOKS = ["commit-msg", "pre-commit", "pre-push"]
ADR = ".about/adr/repo-setup.md"
HATHI = ".hathi.yml"
HATHI_PIN = '"github:bunderlog/hathi"'
HATHI_OLDEST = (1, 2, 0)
COMMITLINT = [
    "commitlint.config.js", "commitlint.config.cjs", "commitlint.config.mjs",
    "commitlint.config.ts", ".commitlintrc", ".commitlintrc.json", ".commitlintrc.yml",
    ".commitlintrc.yaml", ".commitlintrc.js", ".commitlintrc.cjs",
]
READMES = ["README.md", "README", "README.markdown", "readme.md"]
# A pre-commit hook of the project's own that checks for Secrets, where it runs no hathi.
SECRETS_TOOL = re.compile(r"\b(gitleaks|trufflehog|detect-secrets|git-secrets|ggshield)\b")
# The Git hook managers setup doesn't edit, by the file that shows one, and what to say of it.
OTHER_MANAGERS = [
    ("lefthook.yml", "lefthook.yml"), (".lefthook.yml", ".lefthook.yml"),
    ("lefthook.yaml", "lefthook.yaml"), (".pre-commit-config.yaml", "pre-commit's config"),
]


class Stop(Exception):
    """Why a run can't set the repo up; it has written nothing."""


@dataclass
class _Layout:
    """Where the repo's Git hooks live: the folder, from the root, and the command that turns
    them on in a clone, with the core.hooksPath it sets."""

    folder: str
    command: str
    sentence: str
    hooks_path: str


GITHOOKS = _Layout(
    ".githooks", "git config core.hooksPath .githooks",
    "Turn the Git hooks in `.githooks/` on once in each clone: `git config core.hooksPath "
    ".githooks`.",
    ".githooks",
)
HUSKY = _Layout(
    ".husky", "npm install",
    "`npm install` turns the Git hooks in `.husky/` on, through husky.",
    ".husky/_",
)


def _layout(root: str) -> _Layout:
    """Where the repo at `root` keeps its Git hooks; Stop for a manager setup doesn't edit."""
    for file, what in OTHER_MANAGERS:
        if os.path.exists(os.path.join(root, file)):
            raise Stop(f"the repo runs its Git hooks with {what}, which setup doesn't edit: add "
                       "`hathi check <hook>` to it by hand")
    package = _json(os.path.join(root, "package.json"))
    if isinstance(package.get("husky"), dict) and "hooks" in package["husky"]:
        raise Stop("the repo has husky's hooks in package.json, an older husky setup doesn't "
                   "edit: move to husky's .husky/ folder first")
    if os.path.isdir(os.path.join(root, HUSKY.folder)):
        return HUSKY
    return GITHOOKS


@dataclass
class _Item:
    """One item of the list, as doctor names it, and whether the repo has it."""

    name: str
    present: bool


def started(root: str) -> bool:
    """Whether the repo at `root` was set up at all: its .claude/settings.json turns baloo on."""
    plugins = _json(os.path.join(root, names.PROJECT_SETTINGS)).get("enabledPlugins")
    return isinstance(plugins, dict) and plugins.get(PLUGINS[0]) is True


def hooks_off(root: str) -> str:
    """The command that turns on the Git hooks git tracks in the repo at `root`, in a layout setup
    knows, where this clone hasn't turned them on; "" otherwise (PRD visibility)."""
    for where in (GITHOOKS, HUSKY):
        p = subprocess.run(["git", "--no-optional-locks", "-C", root, "ls-files", "--",
                            where.folder], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True)
        if p.stdout.strip():
            return "" if _git_config(root, "core.hooksPath") == where.hooks_path else where.command
    return ""


def missing(root: str) -> List[str]:
    """The items of the list the repo at `root` lacks, by name."""
    return [i.name for i in _items(root) if not i.present]


def _items(root: str) -> List[_Item]:
    """Each item of the list that applies to the repo at `root`, and whether it has it."""
    s = _json(os.path.join(root, names.PROJECT_SETTINGS))
    has_hathi = os.path.exists(os.path.join(root, HATHI))
    try:
        where: Optional[_Layout] = _layout(root)
    except Stop:
        where = None
    out = [
        _Item("the bunderlog marketplace in .claude/settings.json", _marketplace(s)),
        _Item("baloo and louie on in .claude/settings.json", _plugins_on(s)),
        _Item("enableWorkflows in .claude/settings.json", s.get("enableWorkflows") is True),
        _Item("the permissions.deny rules on Env files and private keys in .claude/settings.json",
             not [r for r in DENY if r not in _deny(s)]),
        _Item("attribution off in .claude/settings.json",
             s.get("attribution") == {"commit": "", "pr": ""}),
        _Item("no statusLine or outputStyle in .claude/settings.json",
             "statusLine" not in s and "outputStyle" not in s),
    ]
    fmt = _format_file(root, has_hathi)
    if fmt:
        out.append(_Item(f"the line importing {fmt} in CLAUDE.md",
                        _imports(_read(os.path.join(root, "CLAUDE.md")), fmt)))
    if has_hathi:
        out.append(_Item(".hathi.yml listing conventional-commits' types",
                        _types_listed(_read(os.path.join(root, HATHI)))))
    hooks_ok = False
    if where is None:
        out.append(_Item("Git hooks setup can read", False))
    elif has_hathi:
        hooks_ok = all(_hathi_first(_read(os.path.join(root, where.folder, h)), h) for h in HOOKS)
        out.append(_Item(f"the Git hooks in {where.folder}/ running hathi first", hooks_ok))
    else:
        hooks_ok = bool(SECRETS_TOOL.search(_read(os.path.join(root, where.folder, "pre-commit"))))
        out.append(_Item(f"a pre-commit hook in {where.folder}/ that checks for Secrets",
                        hooks_ok))
    if where is not None and hooks_ok:
        doc = _command_file(root)
        out.append(_Item(f"the command that turns the Git hooks on, in {doc}",
                        where.command in _read(os.path.join(root, doc))))
    ignored = _read(os.path.join(root, ".gitignore"))
    for pattern in IGNORED:
        out.append(_Item(f"{pattern} in .gitignore", _ignores(ignored, pattern)))
    mise = os.path.join(root, "mise.toml")
    if has_hathi and os.path.exists(mise):
        pin = _pin(_read(mise))
        out.append(_Item("hathi pinned to an exact version in mise.toml",
                        pin is not None and _exact(pin)))
    out.append(_Item(f"the ADR {ADR} on how this repo is set up",
                    os.path.exists(os.path.join(root, ADR))))
    return out


@dataclass
class Result:
    """What a run wrote and removed, by path from the root, and what is left for the skill and the
    person."""

    changed: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    left: List[str] = field(default_factory=list)


def run(root: str, add_hathi: Optional[bool]) -> Result:
    """Sets the repo at `root` up: `add_hathi` says whether to add hathi where the repo has no
    .hathi.yml, and is ignored where it has one. It raises Stop before writing anything where it
    can't."""
    has_hathi = os.path.exists(os.path.join(root, HATHI))
    if not has_hathi and add_hathi is None:
        raise Stop("the repo has no .hathi.yml: ask the user whether to add hathi, then run "
                   "setup with --hathi or --no-hathi")
    hathi = has_hathi or bool(add_hathi)
    where = _layout(root)
    version = ""
    if hathi:
        version = _hathi_version()
    writes: Dict[str, Optional[str]] = {}
    modes: Dict[str, int] = {}

    def now(rel: str) -> str:
        """The file `rel` as this run leaves it so far."""
        got = writes.get(rel, "")
        return got if rel in writes and got is not None else _read(os.path.join(root, rel))

    def put(rel: str, text: Optional[str], mode: int = 0) -> None:
        path = os.path.join(root, rel)
        if text is None:
            if os.path.lexists(path):
                writes[rel] = None
        elif text != _read(path) or not os.path.exists(path):
            writes[rel] = text
            if mode:
                modes[rel] = mode

    put(names.PROJECT_SETTINGS, _settings(_json_strict(os.path.join(root, names.PROJECT_SETTINGS))))
    fmt = HATHI if hathi else _format_file(root, False)
    if fmt:
        put("CLAUDE.md", _import(now("CLAUDE.md"), fmt))
    if hathi:
        if not has_hathi:
            put(HATHI, _hathi_config())
        elif not _types_listed(_read(os.path.join(root, HATHI))):
            put(HATHI, _add_types(_read(os.path.join(root, HATHI))))
        for hook in HOOKS:
            rel = os.path.join(where.folder, hook)
            text = _read(os.path.join(root, rel))
            text = _drop_baloo_lines(text)
            if not text.strip() and where is GITHOOKS:
                text = _hathi(["hooks", "print", hook])
            elif not _hathi_first(text, hook):
                text = _put_first(text, f'hathi check {hook} "$@" || exit $?')
            put(rel, text, 0o755)
    hooks_ok = hathi or bool(
        SECRETS_TOOL.search(_read(os.path.join(root, where.folder, "pre-commit"))))
    if hooks_ok:
        doc = _command_file(root)
        text = now(doc)
        if where.command not in text:
            put(doc, _add_to_development(text, where.sentence))
    put(".gitignore", _ignore(_read(os.path.join(root, ".gitignore"))))
    mise = os.path.join(root, "mise.toml")
    if hathi and os.path.exists(mise):
        put("mise.toml", _pin_in(_read(mise), version))
    put(names.OLD_CONFIG, None)
    local = _json(os.path.join(root, names.LOCAL_SETTINGS))
    kept = {k: v for k, v in local.items() if k not in baloo_local(local)}
    if kept != local:
        put(names.LOCAL_SETTINGS, json.dumps(kept, indent=2) + "\n")
    hooks_dir = os.path.join(settings.git_dir(root), "hooks")
    for name in sorted(os.listdir(hooks_dir)) if os.path.isdir(hooks_dir) else []:
        path = os.path.join(hooks_dir, name)
        if os.path.isfile(path) and names.OLD_MARKER in _read(path):
            writes[path] = None

    for rel, text in writes.items():
        path = os.path.join(root, rel)
        if text is None:
            os.remove(path)
            continue
        os.makedirs(os.path.dirname(path) or root, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        if rel in modes:
            os.chmod(path, modes[rel])
    rel = {r: os.path.relpath(os.path.join(root, r), root) for r in writes}
    result = Result(changed=sorted(rel[r] for r, t in writes.items() if t is not None),
                    removed=sorted(rel[r] for r, t in writes.items() if t is None))
    if not os.path.exists(os.path.join(root, ADR)):
        result.left.append(
            f"write {ADR}: whether the repo runs hathi, what checks Secrets, and what an earlier "
            "baloo left that this run removed")
    if hooks_ok and _git_config(root, "core.hooksPath") != where.hooks_path:
        result.left.append(f"turn the Git hooks on in this clone: {where.command}")
    return result


def baloo_local(local: Dict[str, Any]) -> List[str]:
    """The keys of the clone's settings.local.json `local` an earlier baloo wrote: its statusLine
    and the outputStyle it picked."""
    found = []
    if statusline.ours(local.get("statusLine")):
        found.append("statusLine")
    style = local.get("outputStyle")
    if isinstance(style, str) and style.startswith(names.OLD_MARKER.split()[-1] + ":"):
        found.append("outputStyle")
    return found


def _settings(s: Dict[str, Any]) -> str:
    """The project's settings `s` with the list's: the marketplace, baloo and louie on, Workflows
    on, the deny rules, attribution off, and no statusLine or outputStyle; the rest as it was."""
    s = dict(s)
    markets = dict(s.get("extraKnownMarketplaces") or {})
    if not _marketplace(s):
        markets[names.MARKETPLACE] = {"source": dict(MARKETPLACE_SOURCE)}
    s["extraKnownMarketplaces"] = markets
    plugins = dict(s.get("enabledPlugins") or {})
    for p in PLUGINS:
        plugins[p] = True
    s["enabledPlugins"] = plugins
    s["enableWorkflows"] = True
    permissions = dict(s.get("permissions") or {})
    deny = list(permissions.get("deny") or [])
    permissions["deny"] = deny + [r for r in DENY if r not in deny]
    s["permissions"] = permissions
    s["attribution"] = {"commit": "", "pr": ""}
    s.pop("statusLine", None)
    s.pop("outputStyle", None)
    return json.dumps(s, indent=2, ensure_ascii=False) + "\n"


def _marketplace(s: Dict[str, Any]) -> bool:
    markets = s.get("extraKnownMarketplaces")
    if not isinstance(markets, dict) or not isinstance(markets.get(names.MARKETPLACE), dict):
        return False
    return markets[names.MARKETPLACE].get("source") == MARKETPLACE_SOURCE


def _plugins_on(s: Dict[str, Any]) -> bool:
    plugins = s.get("enabledPlugins")
    return isinstance(plugins, dict) and all(plugins.get(p) is True for p in PLUGINS)


def _deny(s: Dict[str, Any]) -> List[str]:
    permissions = s.get("permissions")
    deny = permissions.get("deny") if isinstance(permissions, dict) else None
    return deny if isinstance(deny, list) else []


def _format_file(root: str, has_hathi: bool) -> str:
    """The file setting the repo's commit format, which CLAUDE.md imports: .hathi.yml, else the
    project's commitlint config, else ""."""
    if has_hathi:
        return HATHI
    for name in COMMITLINT:
        if os.path.exists(os.path.join(root, name)):
            return name
    return ""


def _imports(text: str, fmt: str) -> bool:
    return re.search(r"(^|\s)@" + re.escape(fmt) + r"(?=[\s.,;:)]|$)", text) is not None


def _import(text: str, fmt: str) -> str:
    """CLAUDE.md's `text` with a line importing the format file `fmt`, unless it has one."""
    if _imports(text, fmt):
        return text
    line = f"Commit messages follow `{fmt}`, which the Git hooks check: @{fmt}\n"
    if not text:
        return "# CLAUDE.md\n\n" + line
    return text + ("" if text.endswith("\n") else "\n") + "\n" + line


def _types_listed(text: str) -> bool:
    """Whether .hathi.yml's `text` lists conventional-commits' types."""
    block = re.search(r"^conventional-commits:\s*\n((?:[ \t]+.*\n?|\s*\n)*)", text, re.M)
    return block is not None and re.search(r"^[ \t]+types:\s*\[", block.group(1), re.M) is not None


def _default_types() -> str:
    """The types line hathi's defaults list, such as `types: [feat, fix]`."""
    m = re.search(r"^[ \t]+(types:\s*\[[^\]]*\])", _hathi(["config", "--default"]), re.M)
    if not m:
        raise Stop("hathi config --default lists no conventional-commits types")
    return m.group(1)


def _hathi_config() -> str:
    return (
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/bunderlog/hathi/main/"
        "schema.json\n#\n# hathi's settings for this repo: the commit types in full, so Claude "
        "reads the format here\n# through CLAUDE.md; every other Check is on with its defaults.\n"
        f"\nconventional-commits:\n  {_default_types()}\n"
    )


def _add_types(text: str) -> str:
    """.hathi.yml's `text` with the default types; Stop where it has the key without them."""
    if re.search(r"^conventional-commits:", text, re.M):
        raise Stop(".hathi.yml has conventional-commits without its types: list them there by hand")
    return text + ("" if text.endswith("\n") or not text else "\n") + (
        f"\nconventional-commits:\n  {_default_types()}\n")


def _hathi_first(text: str, hook: str) -> bool:
    """Whether the Git hook script `text` runs `hathi check <hook>` before anything else."""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        return re.match(r"(exec\s+)?hathi\s+check\s+" + re.escape(hook) + r"\b", s) is not None
    return False


def _put_first(text: str, line: str) -> str:
    """The Git hook script `text` with `line` first, after its #! line."""
    lines = text.splitlines(keepends=True)
    at = 1 if lines and lines[0].startswith("#!") else 0
    return "".join(lines[:at] + [line + "\n"] + lines[at:])


def _drop_baloo_lines(text: str) -> str:
    return "".join(
        line for line in text.splitlines(keepends=True) if names.OLD_MARKER not in line)


def _command_file(root: str) -> str:
    """The file that gives the command turning the Git hooks on: the README, else CLAUDE.md."""
    for name in READMES:
        if os.path.exists(os.path.join(root, name)):
            return name
    return "CLAUDE.md"


def _add_to_development(text: str, sentence: str) -> str:
    """`text` with `sentence` at the end of its `## Development` section, the section added at
    the end where there is none."""
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if re.match(r"##\s+Development\s*$", line)), None)
    if start is None:
        if text and not text.endswith("\n"):
            text += "\n"
        return text + ("\n" if text else "") + f"## Development\n\n{sentence}\n"
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"#{1,2}\s", lines[i])),
               len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    if lines[end - 1] and not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    rest = lines[end:]
    tail = ["\n"] if rest and rest[0].strip() else []
    return "".join(lines[:end] + ["\n", sentence + "\n"] + tail + rest)


def _ignores(text: str, pattern: str) -> bool:
    want = pattern.strip("/")
    return any(line.strip().strip("/") == want for line in text.splitlines())


def _ignore(text: str) -> str:
    for pattern in IGNORED:
        if not _ignores(text, pattern):
            text += ("" if text.endswith("\n") or not text else "\n") + pattern + "\n"
    return text


_PIN = re.compile(r'^(\s*' + re.escape(HATHI_PIN) + r'\s*=\s*)"([^"]*)"', re.M)


def _pin(text: str) -> Optional[str]:
    m = _PIN.search(text)
    return m.group(2) if m else None


def _exact(version: str) -> bool:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    return m is not None and tuple(int(x) for x in m.groups()) >= HATHI_OLDEST


def _pin_in(text: str, version: str) -> str:
    """mise.toml's `text` with hathi pinned to `version`, unless it pins an exact one already."""
    pin = _pin(text)
    if pin is not None:
        return text if _exact(pin) else _PIN.sub(lambda m: f'{m.group(1)}"{version}"', text)
    line = f'{HATHI_PIN} = "{version}"\n'
    m = re.search(r"^\[tools\][ \t]*\n", text, re.M)
    if m:
        return text[: m.end()] + line + text[m.end():]
    return text + ("" if text.endswith("\n") or not text else "\n") + "\n[tools]\n" + line


def _hathi_version() -> str:
    """The installed hathi's version; Stop where there is none, or it is older than 1.2.0."""
    if not shutil.which("hathi"):
        raise Stop("hathi isn't on the PATH: install it with mise or brew, then run setup again")
    version = _hathi(["version"]).strip()
    m = re.fullmatch(r"v?(\d+\.\d+\.\d+)", version)
    if not m or not _exact(m.group(1)):
        raise Stop(f"hathi {version} is older than 1.2.0: update it, then run setup again")
    return m.group(1)


def _hathi(args: List[str]) -> str:
    try:
        p = subprocess.run(["hathi", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise Stop(f"hathi {' '.join(args)}: {e}") from None
    if p.returncode != 0:
        raise Stop(f"hathi {' '.join(args)}: {p.stderr.strip() or 'exit ' + str(p.returncode)}")
    return p.stdout


def _git_config(root: str, key: str) -> str:
    p = subprocess.run(["git", "-C", root, "config", "--get", key], stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL, text=True)
    return p.stdout.strip()


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _json(path: str) -> Dict[str, Any]:
    """The JSON object in the file at `path`; {} where it isn't one."""
    try:
        return _json_strict(path)
    except Stop:
        return {}


def _json_strict(path: str) -> Dict[str, Any]:
    text = _read(path)
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except ValueError as e:
        raise Stop(f"{path}: {e}") from None
    if not isinstance(value, dict):
        raise Stop(f"{path}: not a JSON object")
    return value
