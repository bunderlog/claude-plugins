import json
import os
import subprocess
import time
import unittest

from bagheera import names, setup, version
from tests import testkit
from tests.bagheera import commands
from tests.bagheera.commands import in_repo, read, run, start, write

# A stand-in for hathi on the PATH: its version, its hook scripts and its default types.
FAKE_HATHI = """#!/bin/sh
case "$1 $2" in
  "version "*) echo 1.2.0 ;;
  "hooks print") printf '#!/bin/sh\\nexec hathi check %s "$@"\\n' "$3" ;;
  "config --default") printf 'conventional-commits:\\n  # The types\\n  types: [feat, fix]\\n' ;;
esac
"""
HOOKS = ["commit-msg", "pre-commit", "pre-push"]
# A stand-in that appends its folder and arguments to the file it names, then runs `then`.
STAND_IN = """#!/bin/sh
printf '%s %s\\n' "$(pwd -P)" "$*" >> '{log}'
{then}
"""
# What the stand-in npm does after recording, as husky's prepare script does.
NPM_OK = "git config core.hooksPath .husky/_"


def tree(dir):
    """Every file under `dir` but .git/, by its path from `dir`, with its content."""
    got = {}
    for folder, dirs, files in os.walk(dir):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in files:
            path = os.path.join(folder, name)
            got[os.path.relpath(path, dir)] = read(path)
    return got


class Setup(unittest.TestCase):
    def setUp(self):
        self.dir = in_repo(self)
        self.bin = testkit.tempdir(self)
        self.logs = testkit.tempdir(self)
        write(os.path.join(self.bin, "hathi"), FAKE_HATHI, 0o755)
        self.stand_in("claude")
        self.stand_in("mise", "exit 1")
        self.stand_in("npm", NPM_OK)
        os.environ["PATH"] = self.bin + os.pathsep + "/usr/bin:/bin"

    def stand_in(self, name, then="exit 0"):
        """Puts a stand-in `name` on the PATH, which records each run for `calls`; `then` is the
        sh it runs after."""
        log = os.path.join(self.logs, name)
        write(os.path.join(self.bin, name), STAND_IN.format(log=log, then=then), 0o755)

    def calls(self, name):
        """Each run of the stand-in `name` so far: the folder it ran in and its arguments."""
        return read(os.path.join(self.logs, name)).splitlines()

    def path(self, rel):
        return os.path.join(self.dir, rel)

    def setup(self, *args):
        code, out, err = run("setup", *args)
        self.assertEqual((code, err), (0, ""), out)
        return out

    def set_up_elsewhere(self):
        """Another project of the machine's, turning baloo on but lacking every other item."""
        other = testkit.repo(self)
        write(os.path.join(other, names.PROJECT_SETTINGS),
              json.dumps({"enabledPlugins": {p: True for p in setup.PLUGINS}}))
        return other

    def settings(self):
        return json.loads(read(self.path(names.PROJECT_SETTINGS)))

    # In a new repo with only a README, setup with hathi added leaves every item of PRD
    # project-setup's list but the ADR, and setup.needs, the ADR written, names none missing.
    def test_new_repo(self):
        write(self.path("README.md"), "# App\n")
        out = self.setup("--hathi")
        s = self.settings()
        self.assertEqual(s["extraKnownMarketplaces"]["bunderlog"]["source"],
                         {"source": "github", "repo": "bunderlog/claude-plugins"})
        self.assertEqual(s["enabledPlugins"], {"baloo@bunderlog": True, "louie@bunderlog": True})
        self.assertIs(s["enableWorkflows"], True)
        self.assertEqual(s["attribution"], {"commit": "", "pr": ""})
        self.assertIn("Read(**/.env)", s["permissions"]["deny"])
        self.assertIn("Read(~/.aws/credentials)", s["permissions"]["deny"])
        self.assertEqual(len(s["permissions"]["deny"]), 14)
        self.assertIn("@.hathi.yml", read(self.path("CLAUDE.md")))
        self.assertIn("conventional-commits:\n  types: [feat, fix]\n",
                      read(self.path(".hathi.yml")))
        for hook in HOOKS:
            path = self.path(os.path.join(".githooks", hook))
            self.assertEqual(read(path), f'#!/bin/sh\nexec hathi check {hook} "$@"\n')
            self.assertTrue(os.access(path, os.X_OK))
        readme = read(self.path("README.md"))
        self.assertIn("## Development\n", readme)
        self.assertIn("git config core.hooksPath .githooks", readme)
        gitignore = read(self.path(".gitignore")).splitlines()
        self.assertIn("/.about/proposals/", gitignore)
        self.assertIn("/.claude/worktrees/", gitignore)
        self.assertIn(".about/adr/repo-setup.md", out)
        self.assertIn("ran:\n  git config core.hooksPath .githooks\n", out)
        self.assertNotIn("core.hooksPath", out.split("left:")[1])
        self.assertEqual(testkit.git(self.dir, "config", "core.hooksPath").strip(), ".githooks")
        self.assertEqual(setup.needs(self.dir), [
            "the ADR .about/adr/repo-setup.md on how this repo is set up is missing"])
        write(self.path(".about/adr/repo-setup.md"), "# This repo runs hathi\n")
        self.assertEqual(setup.needs(self.dir), [])

    # With a mise.toml, hathi is pinned there to the installed version, and a second run keeps it.
    def test_mise_pin(self):
        write(self.path("mise.toml"), '[tools]\nnode = "24"\n')
        self.setup("--hathi")
        self.assertEqual(read(self.path("mise.toml")),
                         '[tools]\n"github:bunderlog/hathi" = "1.2.0"\nnode = "24"\n')

    # In a repo with husky whose pre-commit runs npm test, hathi goes first in each of the three
    # Git hooks there, no .githooks/ is written, and npm install turns them on; an npm install
    # that fails is named with its error, every item still written, and the run exits 1.
    def test_husky(self):
        write(self.path(".husky/pre-commit"), "npm test\n", 0o755)
        out = self.setup("--hathi")
        self.assertEqual(read(self.path(".husky/pre-commit")),
                         'hathi check pre-commit "$@" || exit $?\nnpm test\n')
        for hook in ("commit-msg", "pre-push"):
            self.assertIn(f"hathi check {hook}", read(self.path(".husky/" + hook)))
        self.assertFalse(os.path.exists(self.path(".githooks")))
        self.assertIn("npm install", read(self.path("CLAUDE.md")))
        self.assertEqual(self.calls("npm"), [os.path.realpath(self.dir) + " install"])
        self.assertIn("ran:\n  npm install\n", out)

        self.dir = in_repo(self)
        write(self.path(".husky/pre-commit"), "npm test\n", 0o755)
        self.stand_in("npm", "echo 'npm ERR! no package.json' >&2; exit 2")
        code, out, err = run("setup", "--hathi")
        self.assertEqual((code, err), (1, ""), out)
        self.assertIn("failed:\n  npm install: npm ERR! no package.json\n", out)
        self.assertEqual(setup.missing(self.dir), [
            f"the ADR {setup.ADR} on how this repo is set up"])

    # A pre-push that runs the project's own check and then hathi stays as it is, and setup.needs
    # names only the ADR missing.
    def test_keeps_hathi_last(self):
        hook = '#!/bin/sh\nmise run check </dev/null || exit 1\nexec hathi check pre-push "$@"\n'
        write(self.path(".githooks/pre-push"), hook, 0o755)
        self.setup("--hathi")
        self.assertEqual(read(self.path(".githooks/pre-push")), hook)
        self.assertEqual(setup.needs(self.dir), [
            "the ADR .about/adr/repo-setup.md on how this repo is set up is missing"])

    # The project's own settings stay as they were.
    def test_keeps_settings(self):
        write(self.path(names.PROJECT_SETTINGS), json.dumps({
            "permissions": {"allow": ["Bash(npm test)"], "deny": ["Read(secrets/**)"]},
            "env": {"A": "1"},
        }))
        self.setup("--hathi")
        s = self.settings()
        self.assertEqual(s["permissions"]["allow"], ["Bash(npm test)"])
        self.assertEqual(s["env"], {"A": "1"})
        self.assertEqual(s["permissions"]["deny"][0], "Read(secrets/**)")
        self.assertEqual(len(s["permissions"]["deny"]), 15)

    # What an earlier baloo wrote goes: its Git hooks, a committed outputStyle, its Config and
    # its statusLine in the clone's settings.local.json; a person's own statusLine stays.
    def test_removes_baloo(self):
        hooks = os.path.join(self.dir, ".git", "hooks")
        write(os.path.join(hooks, "pre-commit"), "#!/bin/sh\n# managed by baloo\nexit 0\n", 0o755)
        write(os.path.join(hooks, "pre-rebase.sample"), "#!/bin/sh\n")
        write(self.path(names.PROJECT_SETTINGS), '{"outputStyle": "baloo:short-replies"}')
        write(self.path(names.OLD_CONFIG), "a: 1\n")
        local = self.path(names.LOCAL_SETTINGS)
        write(local, json.dumps({"statusLine": {
            "type": "command", "command": "/x/baloo status-line # managed by baloo"}}))
        self.setup("--hathi")
        self.assertFalse(os.path.exists(os.path.join(hooks, "pre-commit")))
        self.assertTrue(os.path.exists(os.path.join(hooks, "pre-rebase.sample")))
        self.assertNotIn("outputStyle", self.settings())
        self.assertFalse(os.path.exists(self.path(names.OLD_CONFIG)))
        self.assertEqual(json.loads(read(local)), {})

        own = {"statusLine": {"type": "command", "command": "my-line"}}
        write(local, json.dumps(own))
        self.setup()
        self.assertEqual(json.loads(read(local)), own)

    # A husky Git hook's line an earlier baloo added goes, and its own lines stay.
    def test_removes_baloo_line_in_husky(self):
        write(self.path(".husky/pre-commit"),
              'baloo_hook=x; "$baloo_hook" || exit $? # managed by baloo\nnpm run lint\n', 0o755)
        self.setup("--hathi")
        self.assertEqual(read(self.path(".husky/pre-commit")),
                         'hathi check pre-commit "$@" || exit $?\nnpm run lint\n')

    # CLAUDE.md keeps its text, and gets one line importing .hathi.yml.
    def test_claude_md(self):
        write(self.path("CLAUDE.md"), "# CLAUDE.md\n\nRun make test.\n")
        self.setup("--hathi")
        text = read(self.path("CLAUDE.md"))
        self.assertTrue(text.startswith("# CLAUDE.md\n\nRun make test.\n"))
        self.assertEqual(text.count("@.hathi.yml"), 1)

    # A second run changes no file, makes no commit, and git's config differs only in the
    # core.hooksPath that turns the Git hooks on.
    def test_second_run(self):
        write(self.path("README.md"), "# App\n\n## Development\n\nRun it.\n\n## License\n\nMIT\n")
        write(self.path("mise.toml"), '[tools]\n')
        config = testkit.git(self.dir, "config", "--local", "--list")
        self.setup("--hathi")
        first = tree(self.dir)
        self.assertIn("Run it.\n\nTurn the Git hooks", first["README.md"])
        self.assertTrue(first["README.md"].endswith("## License\n\nMIT\n"))
        self.assertIn("nothing to change", self.setup())
        self.assertEqual(tree(self.dir), first)
        self.assertEqual(testkit.git(self.dir, "config", "--local", "--list"),
                         config + "core.hookspath=.githooks\n")
        p = subprocess.run(["git", "-C", self.dir, "rev-parse", "--verify", "-q", "HEAD"],
                           stdout=subprocess.PIPE)
        self.assertNotEqual(p.returncode, 0, "setup made a commit")

    # Setup stops and writes nothing: hathi asked for and neither it nor mise on the PATH, husky's
    # setup in package.json, lefthook, and a repo without .hathi.yml that didn't say whether to add
    # it.
    def test_stops(self):
        write(self.path("README.md"), "# App\n")
        before = tree(self.dir)
        os.environ["PATH"] = "/usr/bin:/bin"
        for files, args, why in [
            ({}, ["--hathi"], "mise isn't on the PATH to install it: install mise first "
             "(curl https://mise.run | sh)"),
            ({"package.json": '{"husky": {"hooks": {"pre-commit": "npm test"}}}'}, ["--hathi"],
             "husky's hooks in package.json"),
            ({"lefthook.yml": "pre-commit:\n"}, ["--no-hathi"], "lefthook.yml"),
            ({}, [], "--hathi or --no-hathi"),
        ]:
            with self.subTest(why=why):
                for rel, text in files.items():
                    write(self.path(rel), text)
                code, out, err = run("setup", *args)
                self.assertEqual((code, out), (1, ""))
                self.assertIn(why, err)
                self.assertEqual(tree(self.dir), {**before, **files})
                for rel in files:
                    os.remove(self.path(rel))

    # setup --in completes another project that is set up, writing nothing in the session's own
    # repo and making no commit there; one that isn't set up it names and leaves alone (PRD setup).
    def test_in_another_project(self):
        self.setup("--hathi")
        mine = tree(self.dir)
        other = testkit.repo(self)
        write(os.path.join(other, "README.md"), "# Other\n")

        # Not set up at all: its owner's to set up from a session there.
        code, out, err = run("setup", "--in", other)
        self.assertEqual(code, 1, out)
        self.assertIn("doesn't turn baloo on: run /bagheera:setup in a session there", err)
        self.assertEqual(tree(other), {"README.md": "# Other\n"})

        # Set up but lacking items: the run completes it.
        write(os.path.join(other, names.PROJECT_SETTINGS),
              json.dumps({"enabledPlugins": {p: True for p in setup.PLUGINS}}))
        code, out, err = run("setup", "--in", other, "--hathi")
        self.assertEqual((code, err), (0, ""), out)
        # Only the ADR is left, which the skill writes, as in the session's own repo.
        missing = setup.missing(other)
        self.assertEqual(len(missing), 1, missing)
        self.assertIn(setup.ADR, missing[0])
        self.assertEqual(tree(self.dir), mine, "it wrote in the session's own repo")
        self.assertEqual(
            subprocess.run(["git", "-C", other, "log", "--oneline"], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, text=True).stdout, "",
            "it committed in the other project")

    # Of two projects, the one whose run stops is named with what stopped it and nothing is
    # written there; the other is still completed (PRD setup).
    def test_in_another_project_stops(self):
        stops, works = (self.set_up_elsewhere() for _ in range(2))
        write(os.path.join(stops, "package.json"),
              '{"husky": {"hooks": {"pre-commit": "npm test"}}}')
        before = tree(stops)
        code, out, err = run("setup", "--in", stops, "--hathi")
        self.assertEqual(code, 1, out)
        self.assertIn("husky's hooks in package.json", err)
        self.assertEqual(tree(stops), before)
        code, out, err = run("setup", "--in", works, "--hathi")
        self.assertEqual((code, err), (0, ""), out)
        self.assertEqual([m for m in setup.missing(works) if setup.ADR not in m], [])

    # A run with no other project named leaves every other project's files as they were.
    def test_leaves_other_projects(self):
        others = [self.set_up_elsewhere() for _ in range(2)]
        before = [tree(o) for o in others]
        self.setup("--hathi")
        self.assertEqual([tree(o) for o in others], before)

    # setup --others names each project that is set up and lacks an item, has a plugin to install
    # or update, or its Git hooks off, what it needs and whether a run there needs the hathi
    # question answered; with none, it says so.
    def test_others(self):
        self.setup("--hathi")
        self.assertEqual(run("setup", "--others")[1], "no other project to complete\n")
        other = self.set_up_elsewhere()
        folder = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects", "a")
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        done = self.set_up_elsewhere()
        self.assertEqual(run("setup", "--in", done, "--hathi")[0], 0)
        write(os.path.join(done, setup.ADR), "# x\n")
        for n, d in enumerate((other, done)):
            write(os.path.join(folder, f"{n}.jsonl"),
                  json.dumps({"type": "user", "timestamp": stamp, "cwd": d}) + "\n")
        code, out, err = run("setup", "--others")
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn(other + "\n", out)
        self.assertIn("  hathi\tno .hathi.yml: ask whether to add hathi\n", out)
        self.assertIn("attribution off in .claude/settings.json", out)
        self.assertNotIn(self.dir + "\n", out, "it offered the session's own repo")
        self.assertNotIn(done + "\n", out, "it offered a project that needs nothing")

        # Lacking no item, it is still offered for its Git hooks off, or for an old install.
        testkit.git(done, "add", ".githooks")
        testkit.git(done, "config", "--unset", "core.hooksPath")
        out = run("setup", "--others")[1]
        self.assertIn(f"{done}\n  needs\tits Git hooks are off in this clone\n"
                      "  hathi\thas .hathi.yml\n", out)
        testkit.git(done, "config", "core.hooksPath", ".githooks")
        commands.installed(done, **{names.KNOWLEDGE_ID: [
            {"scope": "project", "version": "0.0.1", "projectPath": done}]})
        out = run("setup", "--others")[1]
        self.assertIn(f"{done}\n  needs\t{names.KNOWLEDGE_ID} 0.0.1 is installed, older than the "
                      f"{version.read()} this machine has\n", out)

    # With hathi added and none on the PATH, or one older than 1.2.0, it installs the latest with
    # mise and pins that version in mise.toml; where mise's hathi still isn't on the PATH, it stops
    # naming how to put mise's shims on every shell's PATH, and writes nothing (PRD setup).
    def test_installs_hathi(self):
        newer = os.path.join(testkit.tempdir(self), "hathi")
        write(newer, FAKE_HATHI.replace("echo 1.2.0", "echo 1.4.0"), 0o755)
        hathi = os.path.join(self.bin, "hathi")
        for old in ["", FAKE_HATHI.replace("echo 1.2.0", "echo 1.1.0")]:
            with self.subTest(old=old):
                self.dir = in_repo(self)
                write(self.path("mise.toml"), "[tools]\n")
                if old:
                    write(hathi, old, 0o755)
                elif os.path.exists(hathi):
                    os.remove(hathi)
                ran = len(self.calls("mise"))
                self.stand_in("mise", f"cp '{newer}' '{hathi}'")
                self.setup("--hathi")
                self.assertEqual(len(self.calls("mise")), ran + 1)
                self.assertTrue(self.calls("mise")[-1].endswith(
                    " use --global github:bunderlog/hathi@latest"), self.calls("mise"))
                self.assertIn('"github:bunderlog/hathi" = "1.4.0"', read(self.path("mise.toml")))

        self.dir = in_repo(self)
        write(self.path("README.md"), "# App\n")
        before = tree(self.dir)
        os.remove(hathi)
        self.stand_in("mise")
        code, out, err = run("setup", "--hathi")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("put mise's shims on the PATH of every shell", err)
        self.assertIn("bash -c 'command -v hathi'", err)
        self.assertEqual(tree(self.dir), before)

    # It sets core.hooksPath where it is unset; a clone with a core.hooksPath of its own keeps
    # it, and gets the command named under failed:, with exit 1 (PRD setup).
    def test_hooks_on(self):
        out = self.setup("--hathi")
        self.assertIn("  git config core.hooksPath .githooks\n", out)
        self.assertEqual(testkit.git(self.dir, "config", "core.hooksPath").strip(), ".githooks")

        self.dir = in_repo(self)
        testkit.git(self.dir, "config", "core.hooksPath", "hooks")
        code, out, err = run("setup", "--hathi")
        self.assertEqual((code, err), (1, ""), out)
        self.assertIn("failed:\n  git config core.hooksPath .githooks: core.hooksPath is hooks",
                      out)
        self.assertEqual(testkit.git(self.dir, "config", "core.hooksPath").strip(), "hooks")
        self.assertTrue(os.path.exists(self.path(".githooks/pre-commit")))

    def record(self, **plugins):
        """Records bagheera and the plugins as installed for the repo at the version running,
        `plugins` overriding one by its id."""
        commands.installed(self.dir, **plugins)

    # A plugin the repo turns on with no install of it is installed at project scope, and one
    # older than the bagheera installed is updated at its install's scope, each in the repo, with
    # no committed file changed (PRD setup).
    def test_plugins(self):
        self.setup("--hathi")
        first = tree(self.dir)
        self.record(**{names.BUILD_ID: [], names.KNOWLEDGE_ID: [
            {"scope": "project", "version": "0.0.1", "projectPath": self.dir}]})
        # The real one rewrites the project's settings with their keys reordered.
        self.stand_in("claude", "python3 -c 'import json; p = \".claude/settings.json\"; "
                      "s = json.load(open(p)); json.dump(dict(reversed(list(s.items()))), "
                      "open(p, \"w\"))'")
        out = self.setup()
        here = os.path.realpath(self.dir)
        self.assertEqual(self.calls("claude"), [
            f"{here} plugin update {names.KNOWLEDGE_ID} --scope project",
            f"{here} plugin install {names.BUILD_ID} --scope project",
        ])
        self.assertIn(f"ran:\n  claude plugin update {names.KNOWLEDGE_ID} --scope project\n"
                      f"  claude plugin install {names.BUILD_ID} --scope project\n", out)
        self.assertEqual(tree(self.dir), first)

        # A user install is updated at the user's scope.
        self.record(**{names.KNOWLEDGE_ID: [{"scope": "user", "version": "0.0.1"}]})
        self.assertIn(f"claude plugin update {names.KNOWLEDGE_ID} --scope user\n", self.setup())

    # With no claude on the PATH, or one that exits non-zero, each plugin is named with its
    # command and the error, every other item is written, and the run exits 1 (PRD setup).
    def test_plugins_failed(self):
        for then, error in [(None, "claude isn't on the PATH"),
                            ("echo 'Plugin not found' >&2; exit 1", "Plugin not found")]:
            with self.subTest(error=error):
                self.dir = in_repo(self)
                if then is None:
                    os.remove(os.path.join(self.bin, "claude"))
                else:
                    self.stand_in("claude", then)
                self.record(**{names.KNOWLEDGE_ID: [], names.BUILD_ID: []})
                code, out, err = run("setup", "--hathi")
                self.assertEqual((code, err), (1, ""), out)
                self.assertIn(
                    f"failed:\n  claude plugin install {names.KNOWLEDGE_ID} --scope project: "
                    f"{error}\n  claude plugin install {names.BUILD_ID} --scope project: "
                    f"{error}\n", out)
                self.assertEqual(setup.missing(self.dir), [
                    f"the ADR {setup.ADR} on how this repo is set up"])
                self.assertIn("ran:\n  git config core.hooksPath .githooks\n", out)

    # Without hathi, setup writes no Git hook, and setup.needs names the Secrets check missing.
    def test_no_hathi(self):
        self.setup("--no-hathi")
        self.assertFalse(os.path.exists(self.path(".githooks")))
        self.assertFalse(os.path.exists(self.path(".hathi.yml")))
        self.assertNotIn("@", read(self.path("CLAUDE.md")) if os.path.exists(self.path("CLAUDE.md"))
                         else "")
        missing = setup.needs(self.dir)
        self.assertTrue(any("checks for Secrets" in line for line in missing), missing)

    # setup.needs names, a sentence each, the items a set-up repo lacks, a plugin turned on with
    # no install or with one older than the Release, and Git hooks the repo tracks that its clone
    # hasn't turned on; nothing of a repo that is set up in full, and no item of one that isn't
    # set up at all (PRD setup).
    def test_needs(self):
        self.assertEqual(setup.needs(self.dir), [])
        self.setup("--hathi")
        write(self.path(".about/adr/repo-setup.md"), "# x\n")
        s = self.settings()
        del s["attribution"]
        s["outputStyle"] = "Explanatory"
        write(self.path(names.PROJECT_SETTINGS), json.dumps(s))
        write(self.path(".gitignore"), "/.about/proposals/\n")
        self.assertEqual(setup.needs(self.dir), [
            "attribution off in .claude/settings.json is missing",
            "statusLine or outputStyle in .claude/settings.json, where each person sets their own",
            "/.claude/worktrees/ in .gitignore is missing",
        ])

        self.dir = in_repo(self)
        commands.set_up(self.dir)
        testkit.git(self.dir, "add", ".githooks")
        testkit.git(self.dir, "config", "core.hooksPath", ".githooks")
        self.assertEqual(setup.needs(self.dir), [])
        louie = names.BUILD_ID
        commands.installed(self.dir, **{louie: [
            {"scope": "project", "version": "0.0.1", "projectPath": self.dir}]})
        self.assertEqual(setup.needs(self.dir), [
            f"{louie} 0.0.1 is installed, older than the {version.read()} this machine has"])
        commands.installed(self.dir, **{louie: []})
        self.assertEqual(setup.needs(self.dir), [
            f"{louie} is turned on with no install of it for this project"])
        commands.installed(self.dir)
        testkit.git(self.dir, "config", "--unset", "core.hooksPath")
        self.assertEqual(setup.needs(self.dir), ["its Git hooks are off in this clone"])

        # A repo that isn't set up lacks every item, and none of them is a need.
        self.dir = in_repo(self)
        self.assertNotEqual(setup.missing(self.dir), [])
        self.assertEqual(setup.needs(self.dir), [])

    # Session start says once per clone that the repo isn't set up, and never in a set-up repo or
    # a headless session.
    def test_session_start(self):
        told = "this repo isn't set up for bunderlog's plugins"
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "sdk-cli"
        self.assertNotIn(told, start(self)[1])
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        self.assertIn(told, start(self)[1])
        self.assertNotIn(told, start(self)[1])

        self.dir = in_repo(self)
        os.environ["CLAUDE_CODE_ENTRYPOINT"] = "cli"
        self.setup("--no-hathi")
        write(self.path(".githooks/pre-commit"), "#!/bin/sh\ngitleaks protect --staged\n", 0o755)
        write(self.path(".about/adr/repo-setup.md"), "# x\n")
        self.setup("--no-hathi")
        self.assertEqual(setup.needs(self.dir), [])
        self.assertNotIn(told, start(self)[1])


if __name__ == "__main__":
    unittest.main()
