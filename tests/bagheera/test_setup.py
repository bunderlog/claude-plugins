import json
import os
import subprocess
import time
import unittest

from bagheera import names, setup
from tests import testkit
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
        bin = testkit.tempdir(self)
        write(os.path.join(bin, "hathi"), FAKE_HATHI, 0o755)
        os.environ["PATH"] = bin + os.pathsep + "/usr/bin:/bin"

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

    def doctor_missing(self):
        """The lines doctor names missing items with."""
        start(self)
        out = run("doctor")[1]
        return [line for line in out.splitlines() if "/bagheera:setup" in line]

    # In a new repo with only a README, setup with hathi added leaves every item of PRD
    # project-setup's list but the ADR, and doctor, the ADR written, names none missing.
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
        self.assertIn("git config core.hooksPath .githooks", out)
        self.assertEqual(self.doctor_missing(), [
            "- the ADR .about/adr/repo-setup.md on how this repo is set up is missing: "
            "/bagheera:setup fixes it"])
        write(self.path(".about/adr/repo-setup.md"), "# This repo runs hathi\n")
        self.assertEqual(self.doctor_missing(), [])

    # With a mise.toml, hathi is pinned there to the installed version, and a second run keeps it.
    def test_mise_pin(self):
        write(self.path("mise.toml"), '[tools]\nnode = "24"\n')
        self.setup("--hathi")
        self.assertEqual(read(self.path("mise.toml")),
                         '[tools]\n"github:bunderlog/hathi" = "1.2.0"\nnode = "24"\n')

    # In a repo with husky whose pre-commit runs npm test, hathi goes first in each of the three
    # Git hooks there, and no .githooks/ is written.
    def test_husky(self):
        write(self.path(".husky/pre-commit"), "npm test\n", 0o755)
        self.setup("--hathi")
        self.assertEqual(read(self.path(".husky/pre-commit")),
                         'hathi check pre-commit "$@" || exit $?\nnpm test\n')
        for hook in ("commit-msg", "pre-push"):
            self.assertIn(f"hathi check {hook}", read(self.path(".husky/" + hook)))
        self.assertFalse(os.path.exists(self.path(".githooks")))
        self.assertIn("npm install", read(self.path("CLAUDE.md")))

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

    # A second run changes no file, makes no commit and leaves git's config as it was.
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
        self.assertEqual(testkit.git(self.dir, "config", "--local", "--list"), config)
        p = subprocess.run(["git", "-C", self.dir, "rev-parse", "--verify", "-q", "HEAD"],
                           stdout=subprocess.PIPE)
        self.assertNotEqual(p.returncode, 0, "setup made a commit")

    # Setup stops and writes nothing: hathi asked for and not on the PATH, husky's setup in
    # package.json, lefthook, and a repo without .hathi.yml that didn't say whether to add it.
    def test_stops(self):
        write(self.path("README.md"), "# App\n")
        before = tree(self.dir)
        os.environ["PATH"] = "/usr/bin:/bin"
        for files, args, why in [
            ({}, ["--hathi"], "install it with mise or brew"),
            ({"package.json": '{"husky": {"hooks": {"pre-commit": "npm test"}}}'}, ["--hathi"],
             "husky's hooks in package.json"),
            ({"lefthook.yml": "pre-commit:\n"}, ["--no-hathi"], "lefthook.yml"),
            ({}, [], "--hathi or --no-hathi"),
        ]:
            with self.subTest(why=why):
                for rel, text in files.items():
                    write(self.path(rel), text)
                code, out, err = run("setup", *args)
                self.assertEqual(code, 1, out)
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

    # setup --others names each project that is set up and lacks an item, what it lacks and
    # whether a run there needs the hathi question answered; with none, it says so.
    def test_others(self):
        self.setup("--hathi")
        self.assertEqual(run("setup", "--others")[1], "no other project to complete\n")
        other = self.set_up_elsewhere()
        folder = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects", "a")
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        write(os.path.join(folder, "1.jsonl"),
              json.dumps({"type": "user", "timestamp": stamp, "cwd": other}) + "\n")
        code, out, err = run("setup", "--others")
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn(other + "\n", out)
        self.assertIn("  hathi\tno .hathi.yml: ask whether to add hathi\n", out)
        self.assertIn("attribution off in .claude/settings.json", out)
        self.assertNotIn(self.dir + "\n", out, "it offered the session's own repo")

    # Without hathi, setup writes no Git hook, and doctor names the Secrets check missing.
    def test_no_hathi(self):
        self.setup("--no-hathi")
        self.assertFalse(os.path.exists(self.path(".githooks")))
        self.assertFalse(os.path.exists(self.path(".hathi.yml")))
        self.assertNotIn("@", read(self.path("CLAUDE.md")) if os.path.exists(self.path("CLAUDE.md"))
                         else "")
        missing = self.doctor_missing()
        self.assertTrue(any("checks for Secrets" in line for line in missing), missing)

    # doctor in a set-up repo names each missing item, and only those; a repo where baloo isn't
    # on gets one line.
    def test_doctor(self):
        self.assertEqual(self.doctor_missing(), [
            f"- {self.dir} isn't set up for bunderlog's plugins: /bagheera:setup sets it up"])
        self.setup("--hathi")
        write(self.path(".about/adr/repo-setup.md"), "# x\n")
        s = self.settings()
        del s["attribution"]
        s["outputStyle"] = "Explanatory"
        write(self.path(names.PROJECT_SETTINGS), json.dumps(s))
        write(self.path(".gitignore"), "/.about/proposals/\n")
        self.assertEqual(self.doctor_missing(), [
            "- attribution off in .claude/settings.json is missing: /bagheera:setup fixes it",
            "- statusLine or outputStyle in .claude/settings.json, where each person sets their "
            "own: /bagheera:setup fixes it",
            "- /.claude/worktrees/ in .gitignore is missing: /bagheera:setup fixes it",
        ])

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
        self.assertEqual(self.doctor_missing(), [])
        self.assertNotIn(told, start(self)[1])


if __name__ == "__main__":
    unittest.main()
