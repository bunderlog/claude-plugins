"""`new`, which /louie:new runs: it writes the go-vue template into a new or empty folder outside
any git repo, or stops and writes nothing (PRD templates)."""

import datetime
import json
import os
import shlex
import subprocess
import unittest

from louie import version
from tests import testkit
from tests.louie import commands
from tests.louie.commands import PLUGIN, run

TEMPLATE = os.path.join(PLUGIN, "templates", "go-vue")
MARKS = ("__NAME__", "__OWNER__", "__DATE__")


def files(root):
    """The path from `root` of each file under it, outside .git."""
    found = []
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        found += [os.path.relpath(os.path.join(folder, n), root) for n in names]
    return sorted(found)


def snapshot(root):
    """Every path under `root` with its mode and bytes, .git's included."""
    got = {}
    for folder, dirs, names in os.walk(root):
        for n in dirs + names:
            path = os.path.join(folder, n)
            st = os.lstat(path)
            body = b""
            if os.path.isfile(path) and not os.path.islink(path):
                with open(path, "rb") as f:
                    body = f.read()
            got[os.path.relpath(path, root)] = (st.st_mode, body)
    return got


def text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def git(dir, *args):
    return subprocess.run(
        ["git", "-C", dir, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ).stdout.strip()


class New(unittest.TestCase):
    def setUp(self):
        commands.env(self)
        testkit.repo(self)  # cuts git off from the machine's config for the whole test

    def test_writes_the_template(self):
        for name, make in [("a new folder", False), ("an empty folder", True)]:
            with self.subTest(name):
                dest = os.path.join(commands.outside_repo(self), "new", "demo")
                if make:
                    os.makedirs(dest)
                code, out, err = run("new", dest, "my-app2", "acme")
                self.assertEqual((code, err), (0, ""), out)
                self.check(dest, out)

    def check(self, dest, out):
        today = datetime.date.today().isoformat()
        self.assertEqual(git(dest, "symbolic-ref", "HEAD"), "refs/heads/main")
        self.assertNotEqual(subprocess.run(
            ["git", "-C", dest, "rev-parse", "--verify", "-q", "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).returncode, 0, "a commit was made")
        self.assertEqual(files(dest), sorted([
            ".about/adr/stack.md", ".claude/settings.json", ".githooks/commit-msg",
            ".githooks/pre-commit", ".githooks/pre-push", ".github/workflows/ci.yml",
            ".gitignore", ".hathi.yml", "CLAUDE.md", "mise.toml",
        ]))
        for rel in files(dest):
            body = text(os.path.join(dest, rel))
            for mark in MARKS:
                self.assertNotIn(mark, body, rel)
        for hook in ("commit-msg", "pre-commit", "pre-push"):
            path = os.path.join(dest, ".githooks", hook)
            self.assertTrue(os.access(path, os.X_OK), hook)
            self.assertEqual(text(path), f'#!/bin/sh\nexec hathi check {hook} "$@"\n')

        claude = text(os.path.join(dest, "CLAUDE.md"))
        self.assertTrue(claude.startswith("# my-app2\n"), claude)
        self.assertIn("`acme/my-app2`", claude)
        self.assertIn(": @.hathi.yml", claude)
        self.assertIn("`mise run setup`", claude)
        self.assertIn("git config core.hooksPath\n.githooks", claude)
        stack = text(os.path.join(dest, ".about", "adr", "stack.md"))
        self.assertIn(f"\nDate: {today}\n", stack)
        for part in ("## Considered options", "## Consequences", "hathi", "Secrets", "shellcheck"):
            self.assertIn(part, stack)

        settings = json.loads(text(os.path.join(dest, ".claude", "settings.json")))
        self.assertEqual(settings["extraKnownMarketplaces"]["bunderlog"]["source"],
                         {"source": "github", "repo": "bunderlog/claude-plugins"})
        self.assertEqual(settings["enabledPlugins"],
                         {"baloo@bunderlog": True, "louie@bunderlog": True})
        self.assertIs(settings["enableWorkflows"], True)
        self.assertEqual(settings["attribution"], {"commit": "", "pr": ""})
        self.assertEqual(settings["permissions"]["deny"], [f"Read({p})" for p in [
            "**/.env", "**/.env.local", "**/.env.*.local", "**/.env.development",
            "**/.env.production", "**/.env.staging", "**/.env.test", "**/.envrc", "**/*.pem",
            "**/*.key", "**/id_rsa", "**/id_ed25519", "~/.ssh/id_*", "~/.aws/credentials",
        ]])
        self.assertNotIn("statusLine", settings)
        self.assertNotIn("outputStyle", settings)

        ignored = text(os.path.join(dest, ".gitignore")).splitlines()
        for line in ("/.claude/settings.local.json", "/.about/proposals/", "/.claude/worktrees/"):
            self.assertIn(line, ignored)
        self.assertIn(
            "types: [build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test]",
            text(os.path.join(dest, ".hathi.yml")),
        )
        mise = text(os.path.join(dest, "mise.toml"))
        self.assertIn('"github:bunderlog/hathi" = "1.2.0"', mise)
        self.assertIn('run = "shellcheck .githooks/*"', mise)
        ci = text(os.path.join(dest, ".github", "workflows", "ci.yml"))
        self.assertIn("mise run check", ci)
        self.assertIn("hathi check ci", ci)

        self.assertEqual(out.splitlines()[-1], (
            f"! cd {shlex.quote(dest)} && mise trust && mise run setup && git add -A && "
            f'git commit -m "chore: scaffold from louie go-vue {version.read()}"'
        ))

    # A path with a space or a quote comes back quoted for the shell.
    def test_quotes_the_path(self):
        dest = os.path.join(commands.outside_repo(self), "my 'demo'")
        code, out, _ = run("new", dest, "demo", "acme")
        self.assertEqual(code, 0)
        self.assertIn(f"! cd {shlex.quote(dest)} && ", out.splitlines()[-1])
        self.assertTrue(os.path.isdir(os.path.join(dest, ".git")))

    def test_refuses(self):
        outside = commands.outside_repo(self)
        repo = testkit.repo(self)
        os.makedirs(os.path.join(repo, "sub"))
        cases = []
        for entry in ("x", ".DS_Store"):
            d = os.path.join(outside, "holds-" + entry.strip("."))
            commands.write(os.path.join(d, entry), "x\n")
            cases.append((f"a folder holding {entry}", d, "demo", "holds files"))
        a_file = os.path.join(outside, "a-file")
        commands.write(a_file, "x\n")
        cases += [
            ("a path that is a file", a_file, "demo", "isn't a folder"),
            ("a path below a file", os.path.join(a_file, "demo"), "demo", "isn't a folder"),
            ("a subfolder of a repo", os.path.join(repo, "sub"), "demo", "inside a git repo"),
            ("a new folder in a repo", os.path.join(repo, "sub", "new"), "demo",
             "inside a git repo"),
            ("the repo's root", repo, "demo", "holds files"),
        ]
        for bad in ("Demo", "1demo", "-demo", "de_mo", ""):
            cases.append((f"the name {bad!r}", os.path.join(outside, "new"), bad, "the name"))
        cases.append(("an empty owner", os.path.join(outside, "new"), "demo", "the owner"))
        for what, path, name, why in cases:
            with self.subTest(what):
                before = snapshot(outside), snapshot(repo)
                owner = "" if what == "an empty owner" else "acme"
                code, out, err = run("new", path, name, owner)
                self.assertEqual((code, out), (1, ""), err)
                self.assertTrue(err.startswith("louie: "), err)
                self.assertIn(why, err)
                self.assertEqual((snapshot(outside), snapshot(repo)), before)

    # An empty folder at a repo's root is still inside it.
    def test_refuses_an_empty_repo_root(self):
        repo = testkit.repo(self)
        empty = os.path.join(repo, "empty")
        os.makedirs(empty)
        before = snapshot(repo)
        code, _, err = run("new", empty, "demo", "acme")
        self.assertEqual(code, 1)
        self.assertIn("inside a git repo", err)
        self.assertEqual(snapshot(repo), before)

    # Where git init fails, what was written goes, the folders made for it too.
    def test_removes_what_it_wrote_on_failure(self):
        bin = testkit.tempdir(self)
        commands.write(os.path.join(bin, "git"), "#!/bin/sh\necho broken >&2\nexit 1\n", 0o755)
        os.environ["PATH"] = bin + os.pathsep + os.environ.get("PATH", "")
        outside = commands.outside_repo(self)
        empty = os.path.join(outside, "empty")
        os.makedirs(empty)
        before = snapshot(outside)
        for path in (os.path.join(outside, "new", "demo"), empty):
            with self.subTest(path=path):
                code, out, err = run("new", path, "demo", "acme")
                self.assertEqual((code, out), (1, ""))
                self.assertIn("louie: git init -q --initial-branch=main: broken", err)
                self.assertEqual(snapshot(outside), before)

    def test_usage(self):
        for args in (["new"], ["new", "x"], ["new", "x", "demo"], ["new", "x", "demo", "a", "b"]):
            with self.subTest(args=args):
                self.assertEqual(run(*args)[0], 2)

    # Only the files that would act in this repo by their real name carry the suffix.
    def test_template_suffixes(self):
        suffixed = sorted(f for f in files(TEMPLATE) if f.endswith(".tmpl"))
        self.assertEqual(suffixed, [
            ".claude/settings.json.tmpl", ".gitignore.tmpl", "CLAUDE.md.tmpl", "mise.toml.tmpl",
        ])


if __name__ == "__main__":
    unittest.main()
