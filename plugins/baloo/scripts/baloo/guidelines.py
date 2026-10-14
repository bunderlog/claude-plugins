"""The plugin's Guidelines, the files in its guidelines/ (ADR guidelines): which fit a repo, what
session start tells Claude of the ones the Config turns on, which file the Read tool may read
without asking, and which reach Claude by the file it works on."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple


class _Manifests:
    """What a repo's files say of its stacks and its CI: whether it has a go.mod, the packages its
    package.json files depend on, whether it has any package manager's manifest, and whether its
    root holds a CI's config."""

    def __init__(self) -> None:
        self.go_mod = False
        self.packages: set = set()
        self.package_manager = False
        self.ci = False


class Guideline(NamedTuple):
    """The file `name`.md in the plugin's guidelines/. `when` is the task that calls for reading
    it, as its index line names it; `fits` says whether a repo's files call for it: they name its
    stack, configure a CI or declare packages; None for a Guideline that fits any project."""

    name: str
    when: str
    fits: Optional[Callable[[_Manifests], bool]] = None


# The plugin's Guidelines, in the order session start names them. Each is a key under guidelines
# in the Config and its schema.
ALL = [
    Guideline(
        "principles",
        "Before non-trivial work (a feature, a refactor, an architecture, API or data-model "
        "change)",
    ),
    Guideline("design", "Designing a module or an interface, or deciding where it is tested from"),
    Guideline("testing", "Writing tests, or building test-first"),
    Guideline(
        "debugging",
        "Finding or fixing the cause of a bug (wrong output, a crash, a failing or flaky test, a "
        "slowdown)",
    ),
    Guideline(
        "writing-for-agents", "Writing or editing a skill, a CLAUDE.md or AGENTS.md, or a prompt"
    ),
    Guideline(
        "ci",
        "Fixing a failed CI run, or finding why a run, a pipeline or a PR went red",
        lambda m: m.ci,
    ),
    Guideline(
        "dependencies",
        "Updating the project's dependencies, all of them or one by name",
        lambda m: m.package_manager,
    ),
    Guideline("go", "Writing Go", lambda m: m.go_mod),
    Guideline("typescript", "Writing TypeScript", lambda m: "typescript" in m.packages),
    Guideline(
        "vue",
        "Writing or testing a Vue component, a composable or a Pinia store, or starting a Vue app",
        lambda m: "vue" in m.packages,
    ),
    Guideline(
        "tailwind",
        "Styling with Tailwind CSS: classes, theme tokens, dark mode",
        lambda m: "tailwindcss" in m.packages,
    ),
]


def names() -> List[str]:
    """The names of ALL, in its order."""
    return [g.name for g in ALL]


# The files and folders at a repo's root that configure a CI.
CI_CONFIGS = [
    ".github/workflows",
    ".gitlab-ci.yml",
    "bitbucket-pipelines.yml",
    "bamboo-specs",
    "Jenkinsfile",
    "azure-pipelines.yml",
    ".circleci",
    ".buildkite",
]

# The files a package manager declares a module's dependencies in.
PACKAGE_MANIFESTS = {"go.mod", "package.json", "Cargo.toml", "pyproject.toml"}

# Folders the stacks and manifests aren't looked for in: another project's code, test fixtures,
# and what a build makes, which can hold more files than the repo's own code.
SKIPPED = {"node_modules", "vendor", "testdata", "build", "dist", "out", "target"}


def fitting(root: str) -> List[str]:
    """The names of the Guidelines that fit the repo at `root`: every one for any project, a
    stack's where a manifest at any depth names it, and dependencies where there is a package
    manager's manifest, both outside hidden folders and the skipped ones, and ci where the root
    holds a CI's config."""
    m = _Manifests()
    m.ci = any(os.path.exists(os.path.join(root, name)) for name in CI_CONFIGS)
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIPPED]
        for name in files:
            if name in PACKAGE_MANIFESTS:
                m.package_manager = True
            if name == "go.mod":
                m.go_mod = True
            elif name == "package.json":
                m.packages.update(_dependencies(os.path.join(folder, name)))
    return [g.name for g in ALL if g.fits is None or g.fits(m)]


def _dependencies(path: str) -> List[str]:
    """The packages the package.json at `path` depends on, of any kind; one that can't be read
    names none."""
    try:
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(p, dict):
        return []
    got: List[str] = []
    for kind in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = p.get(kind)
        if isinstance(deps, dict):
            got.extend(deps)
    return got


# The heading of the section of principles.md that session start prints whole: the rules that
# must hold on every task.
EVERY_TASK = "## On every task"

# The heading of the section of principles.md that session start prints after it where the Bash
# tool's shell is zsh: the rules zsh needs.
IN_ZSH = "## In zsh"


def index(plugin: str, on: Dict[str, bool], shell: str) -> Tuple[str, Optional[str]]:
    """What session start tells Claude of the Guidelines `on` in the plugin at `plugin`: a line for
    each, when to read it and its path, but those given by the file Claude works on (see
    for_file), after the rules for every task when principles is on, and the rules zsh needs where
    `shell`, the Bash tool's, is zsh. With none on it is "". When the rules can't be read, it is
    the lines without them, and why; else why is None."""
    lines = [
        f"- {g.when}: {_path(plugin, g.name)}"
        for g in ALL
        if on.get(g.name) and g.name not in BY_PATH
    ]
    if not lines:
        return "", None
    text = (
        "Guidelines, the plugin's working rules; the project's own CLAUDE.md, config and "
        "linters win where they conflict.\n"
    )
    why = None
    if on.get("principles"):
        principles = _path(plugin, "principles")
        try:
            text += "On every task:\n" + _section(principles, EVERY_TASK) + "\n"
            if shell == "zsh":
                text += "In zsh:\n" + _section(principles, IN_ZSH) + "\n"
        except _Unreadable as e:
            why = str(e)
    return text + "Read a file when its task comes up:\n" + "\n".join(lines), why


def _path(plugin: str, name: str) -> str:
    return os.path.join(plugin, "guidelines", name + ".md")


class _Unreadable(Exception):
    """Why a Guideline's section can't be read."""


def _section(file: str, heading: str) -> str:
    """The text under the line `heading` in the Markdown file at `file`, up to the next heading of
    its level, whatever its line endings and the spaces around the heading."""
    try:
        with open(file, encoding="utf-8", newline="") as f:
            data = f.read()
    except OSError as e:
        raise _Unreadable(_os_error("open", file, e)) from e
    level = heading[: heading.index(" ") + 1]
    body: List[str] = []
    inside = False
    for line in data.replace("\r\n", "\n").split("\n"):
        if line.strip() == heading:
            inside = True
        elif inside and line.startswith(level):
            return "\n".join(body).strip()
        elif inside:
            body.append(line.rstrip(" \t"))
    if not inside:
        raise _Unreadable(f'{file} has no "{heading}"')
    return "\n".join(body).strip()


def _os_error(op: str, path: str, e: OSError) -> str:
    """`e` as Go words it, such as `open <path>: no such file or directory`."""
    return f"{op} {path}: {os.strerror(e.errno).lower() if e.errno else e}"


def readable(plugin: str, file: str) -> bool:
    """Whether `file` is a Guideline file of the plugin at `plugin`, a file right in its
    guidelines/, once links are followed; a path that isn't absolute is none."""
    if not plugin or not os.path.isabs(file):
        return False
    folder = os.path.join(plugin, "guidelines")
    if not os.path.exists(folder) or not os.path.exists(file):
        return False
    real = os.path.realpath(file)
    return os.path.isfile(real) and os.path.dirname(real) == os.path.realpath(folder)


def _has_ext(*exts: str) -> Callable[[str], bool]:
    return lambda rel: os.path.splitext(rel)[1] in exts


def _is_test(rel: str) -> bool:
    """Whether the file at `rel` is a test: Go's, Python's, or a JavaScript or TypeScript one by
    its name or its __tests__ folder."""
    name = os.path.basename(rel)
    stem = os.path.splitext(name)[0]
    return (
        name.endswith("_test.go")
        or (name.endswith(".py") and (name.startswith("test_") or stem.endswith("_test")))
        or stem.endswith(".test")
        or stem.endswith(".spec")
        or "__tests__" in os.path.dirname(rel).replace(os.sep, "/").split("/")
    )


# The Guidelines that reach Claude by the file it works on, not by its own choice (ADR
# guidelines): each says whether a file, by its path from the repo's root, is one of its subject.
# Session start's index leaves them out.
BY_PATH: Dict[str, Callable[[str], bool]] = {
    "typescript": _has_ext(".ts", ".tsx", ".mts", ".cts", ".vue"),
    "vue": _has_ext(".vue"),
    "testing": _is_test,
}

# How long what a session was given is kept: a week.
KEPT = 7 * 24 * 3600


def for_file(plugin: str, data: str, session: str, rel: str, on: Dict[str, bool]) -> str:
    """What Claude is to be told of the Guidelines `on` whose subject the file at `rel`, from the
    repo's root, is, and that the session `session` hasn't been given yet: each one's whole text,
    from the plugin at `plugin`. Each one given is marked for the session and logged in the
    plugin's data folder `data`, a line each: when, in UTC, the session, the Guideline and `rel`.
    It is "" where none is due. A file it can't read or write raises OSError."""
    due = [g.name for g in ALL if g.name in BY_PATH and on.get(g.name) and BY_PATH[g.name](rel)]
    if not due or not data:  # without its data folder, it can't give each one only once
        return ""
    folder = os.path.join(data, "guidelines")
    shown = os.path.join(folder, "shown")
    _forget(shown)
    seen = os.path.join(shown, session)
    given = _lines(seen)
    text: List[str] = []
    new: List[str] = []
    for name in due:
        if name in given:
            continue
        with open(_path(plugin, name), encoding="utf-8") as f:
            body = f.read()
        text.append(
            f"The {name} Guideline applies to {rel}, which you just read or changed; follow it "
            f"for the rest of this session:\n\n{body.strip()}"
        )
        new.append(name)
    if not new:
        return ""
    os.makedirs(shown, mode=0o700, exist_ok=True)
    if session:
        _write(seen, "\n".join(given + new) + "\n")
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_path = os.path.join(folder, "guidelines.log")
    fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as log:
        for name in new:
            log.write(f"{at}\t{session}\t{name}\t{rel.replace(os.sep, '/')}\n")
    return "\n\n".join(text)


def _write(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)


def _lines(file: str) -> List[str]:
    """The lines of the file at `file`, none where it can't be read."""
    try:
        with open(file, encoding="utf-8") as f:
            return [line for line in f.read().splitlines() if line]
    except OSError:
        return []


def _forget(folder: str) -> None:
    """Deletes what sessions were given more than a week ago."""
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return
    now = time.time()
    for e in entries:
        try:
            if now - e.stat().st_mtime > KEPT:
                os.remove(e.path)
        except OSError:
            pass
