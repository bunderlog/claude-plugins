"""`new`, which /louie:new runs: it writes the go-vue template into a new or empty folder outside
any git repo, or stops and writes nothing (PRD templates)."""

import datetime
import json
import os
import re
import shlex
import subprocess
import unittest

from louie import version
from tests import testkit
from tests.louie import commands
from tests.louie.commands import PLUGIN, run

TEMPLATE = os.path.join(PLUGIN, "templates", "go-vue")
MARKS = ("__NAME__", "__OWNER__", "__DATE__")
# hathi's Secret Check: a password in a URL unless it is a placeholder, and an Env file unless it is
# a template of one.
URL_PASSWORD = re.compile(r"\b[A-Za-z][A-Za-z0-9+.-]*://[^\t-\r :/@]*:[^\t-\r /@$<{*][^\t-\r /@]*@")
ENV_FILE = re.compile(r"(^|/)(\.env(\.[^/]*)?|\.envrc|[^/]*\.env)$")
ENV_TEMPLATE = re.compile(r"\.(example|sample|template|dist)$")


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
            ".gitignore", ".hathi.yml", "CLAUDE.md", "mise.toml", "README.md",
            "Dockerfile", ".dockerignore", "docker-compose.yml", "config/deploy.yml",
            ".kamal/secrets", ".env.example",
            "apps/api/go.mod", "apps/api/go.sum", "apps/api/sqlc.yaml",
            "apps/api/cmd/server/main.go", "apps/api/internal/handler/handler.go",
            "apps/api/internal/handler/handler_test.go", "apps/api/internal/handler/app.go",
            "apps/api/internal/handler/app_test.go", "apps/api/internal/respond/respond.go",
            "apps/api/internal/database/database.go",
            "apps/api/internal/database/database_test.go", "apps/api/migrations/migrations.go",
            "apps/api/internal/db/db.go", "apps/api/internal/db/models.go",
            "apps/api/internal/db/notes.sql.go", "apps/api/migrations/00001_notes.sql",
            "apps/api/queries/notes.sql",
            "package.json", "pnpm-workspace.yaml", "pnpm-lock.yaml",
            "apps/app/package.json", "apps/app/index.html", "apps/app/tsconfig.json",
            "apps/app/vite.config.ts", "apps/app/eslint.config.ts", "apps/app/.prettierrc.json",
            "apps/app/.prettierignore", "apps/app/src/env.d.ts", "apps/app/src/app/main.ts",
            "apps/app/src/app/App.vue", "apps/app/src/app/router.ts", "apps/app/src/app/main.css",
            "apps/app/src/views/HomeView.vue", "apps/app/src/views/HomeView.test.ts",
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
        for part in ("## Considered options", "## Consequences", "hathi", "Secrets", "shellcheck",
                     "Go", "sqlc", "goose", "`GET /api/up`", "`github.com/acme/my-app2`",
                     "Vue", "pnpm", "Tailwind", "over Tailwind"):
            self.assertIn(part, stack)

        api = os.path.join(dest, "apps", "api")
        self.assertEqual(text(os.path.join(api, "go.mod")).splitlines()[0],
                         "module github.com/acme/my-app2")
        go_sum = text(os.path.join(api, "go.sum"))
        for word in ("my-app2", "acme"):
            self.assertNotIn(word, go_sum)
        for rel in ("cmd/server/main.go", "internal/handler/handler.go"):
            self.assertIn('"github.com/acme/my-app2/internal/', text(os.path.join(api, rel)), rel)
        self.assertTrue(text(os.path.join(api, "internal", "db", "db.go")).startswith(
            "// Code generated by sqlc. DO NOT EDIT.\n// versions:\n//   sqlc v1.31.1\n"))
        self.assertIn("-- +goose Up", text(os.path.join(api, "migrations", "00001_notes.sql")))
        self.assertIn("-- name: ListNotes :many", text(os.path.join(api, "queries", "notes.sql")))

        self.assertEqual(json.loads(text(os.path.join(dest, "package.json"))),
                         {"name": "my-app2", "private": True})
        self.assertIn("packages:\n  - apps/app\n",
                      text(os.path.join(dest, "pnpm-workspace.yaml")))
        app = os.path.join(dest, "apps", "app")
        package = json.loads(text(os.path.join(app, "package.json")))
        self.assertEqual(package["name"], "@my-app2/app")
        self.assertNotIn("scripts", package)
        self.assertIn("vue", package["dependencies"])
        for kind in ("dependencies", "devDependencies"):
            for dep, pin in package[kind].items():
                self.assertRegex(pin, r"^\d+\.\d+\.\d+$", dep)
        lock = text(os.path.join(dest, "pnpm-lock.yaml"))
        for word in ("my-app2", "acme"):
            self.assertIsNone(re.search(rf"\b{word}\b", lock), word)
        self.assertIn('"my-app2"', text(os.path.join(app, "src", "views", "HomeView.test.ts")))
        self.assertIn(">my-app2</h1>", text(os.path.join(app, "src", "views", "HomeView.vue")))
        self.assertIn("<title>my-app2</title>", text(os.path.join(app, "index.html")))

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
        for line in ("/.claude/settings.local.json", "/.about/proposals/", "/.claude/worktrees/",
                     "node_modules/", "/apps/app/dist/"):
            self.assertIn(line, ignored)
        self.assertIn(
            "types: [build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test]",
            text(os.path.join(dest, ".hathi.yml")),
        )
        mise = text(os.path.join(dest, "mise.toml"))
        self.assertIn('"github:bunderlog/hathi" = "1.2.0"', mise)
        self.assertIn(
            '\nDATABASE_URL = "postgres://my-app2@localhost:5433/my-app2?sslmode=disable"\n', mise
        )
        self.assertIn('[tasks.dev]\ndescription = ', mise)
        self.assertIn('depends = ["dev:api", "dev:app"]\n', mise)
        self.assertIn('run = "docker compose up -d --wait db"\n', mise)
        self.assertIn('run = "go run ./cmd/server"\n', mise)
        self.assertIn("pnpm exec vite --strictPort", mise)
        self.assertIn("[tasks.deploy]\n", mise)
        self.assertRegex(mise, r"ghcr\.io/basecamp/kamal:v\d+\.\d+\.\d+ ")
        self.assertIn("--env-file .env", mise)
        self.assertNotIn("ruby", mise)
        self.assertNotIn("gem:", mise)
        for pin in ('go = "1.26.10"', 'golangci-lint = "2.15.0"', 'sqlc = "1.31.1"',
                    '"go:github.com/pressly/goose/v3/cmd/goose" = "3.27.2"', 'node = "24.22.1"',
                    'pnpm = "11.28.8"'):
            self.assertIn(pin, mise)
        self.assertIn(
            '  "shellcheck .githooks/*",\n  "cd apps/api && sqlc diff && go build ./... && '
            'go vet ./... && golangci-lint run && go test ./...",\n'
            '  "pnpm install --frozen-lockfile",\n'
            '  "cd apps/app && pnpm exec eslint . && pnpm exec prettier --check . && '
            'pnpm exec vue-tsc --noEmit && pnpm exec vitest run && pnpm exec vite build",\n',
            mise,
        )
        self.assertIn('[tasks.sqlc]\n', mise)
        self.assertIn("\ngo 1.26.10\n", text(os.path.join(api, "go.mod")))
        ci = text(os.path.join(dest, ".github", "workflows", "ci.yml"))
        self.assertIn("mise run check", ci)
        self.assertIn("hathi check ci", ci)
        self.check_deploy(dest, mise, ignored)

        self.assertEqual(out.splitlines()[-1], (
            f"! cd {shlex.quote(dest)} && mise trust && mise run setup && git add -A && "
            f'git commit -m "chore: scaffold from louie go-vue {version.read()}"'
        ))

    # The local database takes no password, and Kamal deploys the Dockerfile's image with the
    # secrets of an ignored .env; only the server and the registry are left for the person.
    def check_deploy(self, dest, mise, ignored):
        self.assertFalse(URL_PASSWORD.search("postgres://u:$PW@localhost/db"))
        for rel in files(dest):
            body = text(os.path.join(dest, rel))
            self.assertIsNone(URL_PASSWORD.search(body), rel)
            self.assertFalse(ENV_FILE.search(rel) and not ENV_TEMPLATE.search(rel), rel)
            if rel not in ("config/deploy.yml", "README.md"):
                for mark in ("<server>", "<registry>"):
                    self.assertFalse(mark in body, f"{rel} holds {mark}")

        compose = text(os.path.join(dest, "docker-compose.yml"))
        self.assertIn("image: postgres:17-alpine\n", compose)
        self.assertIn("POSTGRES_HOST_AUTH_METHOD: trust\n", compose)
        self.assertIn("POSTGRES_USER: my-app2\n", compose)
        self.assertIn(":5433:5432", compose)
        self.assertNotIn("POSTGRES_PASSWORD", compose)

        deploy = text(os.path.join(dest, "config", "deploy.yml"))
        self.assertEqual(set(re.findall(r"<[^<>\s]*>", deploy)), {"<server>", "<registry>"})
        self.assertIn("\nservice: my-app2\nimage: acme/my-app2\n", deploy)
        self.assertIn("  app_port: 8080\n  healthcheck:\n    path: /api/up\n", deploy)
        self.assertIn("  server: <registry>", deploy)
        self.assertIn("\naccessories:\n  db:\n    image: postgres:17-alpine\n", deploy)
        self.assertIn("    host: <server>\n", deploy)

        secrets = text(os.path.join(dest, ".kamal", "secrets"))
        example = text(os.path.join(dest, ".env.example"))
        keys = {line.split("=", 1)[0] for line in example.splitlines()
                if line and not line.startswith("#")}
        self.assertEqual(keys, set(re.findall(r"\$([A-Z_]+)", secrets)))
        for line in example.splitlines():
            if line and not line.startswith("#"):
                self.assertTrue(line.endswith("="), line)
        self.assertIn(
            "\nDATABASE_URL=postgres://my-app2:$POSTGRES_PASSWORD@my-app2-db:5432/", secrets
        )
        for line in ("/.env", "/.env.*", "!/.env.example"):
            self.assertIn(line, ignored)

        dockerfile = text(os.path.join(dest, "Dockerfile"))
        for tool, image in (("go", "golang:{}-alpine"), ("node", "node:{}-alpine"),
                            ("pnpm", "pnpm@{}")):
            pin = re.search(rf'^{tool} = "([^"]+)"', mise, re.M).group(1)
            self.assertIn(image.format(pin), dockerfile, tool)
        self.assertIn("FROM gcr.io/distroless/static-debian12:nonroot\n", dockerfile)
        self.assertIn("ENV APP_DIR=/app ADDR=:8080\n", dockerfile)
        ignore = text(os.path.join(dest, ".dockerignore")).splitlines()
        for line in (".git", ".env", ".env.*", "**/node_modules"):
            self.assertIn(line, ignore)

        api = os.path.join(dest, "apps", "api")
        self.assertIn('"github.com/acme/my-app2/migrations"',
                      text(os.path.join(api, "internal", "database", "database.go")))
        self.assertIn("//go:embed *.sql\n", text(os.path.join(api, "migrations", "migrations.go")))
        main = text(os.path.join(api, "cmd", "server", "main.go"))
        for part in ('"github.com/acme/my-app2/internal/database"', "DATABASE_URL", "APP_DIR",
                     "handler.WithApp("):
            self.assertIn(part, main)
        self.assertIn("github.com/pressly/goose/v3 v3.27.2", text(os.path.join(api, "go.mod")))
        self.assertIn('server: { proxy: { "/api": "http://localhost:8080" } }',
                      text(os.path.join(dest, "apps", "app", "vite.config.ts")))

        stack = text(os.path.join(dest, ".about", "adr", "stack.md"))
        for part in ("Kamal", "kamal-proxy", "`mise run dev`", "`mise run deploy setup`",
                     "git, mise and Docker"):
            self.assertIn(part, stack)
        readme = text(os.path.join(dest, "README.md"))
        self.assertTrue(readme.startswith("# my-app2\n"), readme)
        for part in ("git, mise and Docker",
                     "gh repo create acme/my-app2 --private --source . --push", "mise run dev",
                     "mise run deploy setup", "`<server>`", "`<registry>`", "`.env.example`"):
            self.assertIn(part, readme)

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
        cases = [(what, path, name, "acme", why) for what, path, name, why in cases]
        for bad in ("a b", "a/b", "-acme", "acme-", "ac--me", "ac_me", "", " ", "a" * 40):
            cases.append((f"the owner {bad!r}", os.path.join(outside, "new"), "demo", bad,
                          "the owner"))
        for what, path, name, owner, why in cases:
            with self.subTest(what):
                before = snapshot(outside), snapshot(repo)
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

    # An owner GitHub takes stands in the module's path.
    def test_takes_an_owner(self):
        for owner in ("a", "Acme", "acme-corp", "a1-b2-c3", "a" * 39):
            with self.subTest(owner=owner):
                dest = os.path.join(commands.outside_repo(self), "demo")
                code, _, err = run("new", dest, "demo", owner)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(text(os.path.join(dest, "apps", "api", "go.mod")).splitlines()[0],
                                 f"module github.com/{owner}/demo")

    # Each tool is pinned to an exact version, never a range or latest (ADR stack).
    def test_template_pins_exact_versions(self):
        tools = text(os.path.join(TEMPLATE, "mise.toml.tmpl")).split("[tools]\n", 1)[1]
        tools = tools.split("\n[", 1)[0]
        pins = [line for line in tools.splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(pins), 8, pins)
        for line in pins:
            self.assertRegex(line, r'^\S+ = "\d+\.\d+\.\d+"(  *#.*)?$')

    def test_usage(self):
        for args in (["new"], ["new", "x"], ["new", "x", "demo"], ["new", "x", "demo", "a", "b"]):
            with self.subTest(args=args):
                self.assertEqual(run(*args)[0], 2)

    # Only the files that would act in this repo by their real name carry the suffix.
    def test_template_suffixes(self):
        suffixed = sorted(f for f in files(TEMPLATE) if f.endswith(".tmpl"))
        self.assertEqual(suffixed, [
            ".claude/settings.json.tmpl", ".gitignore.tmpl", "CLAUDE.md.tmpl",
            "apps/api/go.mod.tmpl", "apps/app/package.json.tmpl", "mise.toml.tmpl",
            "package.json.tmpl", "pnpm-workspace.yaml.tmpl",
        ])

    # The template's app follows the vue, typescript and tailwind Guidelines where a search can
    # tell: each component with a script is `<script setup lang="ts">` first, each is styled with
    # theme tokens only, and each TypeScript file opens with a comment.
    def test_template_app_follows_the_guidelines(self):
        app = os.path.join(TEMPLATE, "apps", "app")
        palette = re.compile(
            r"\b(?:bg|text|border|ring|fill|stroke|from|to|via)-(?:white|black|(?:slate|gray|zinc|"
            r"neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|"
            r"violet|purple|fuchsia|pink|rose)-\d+)\b"
        )
        vue = [f for f in files(app) if f.endswith(".vue")]
        ts = [f for f in files(app) if f.endswith(".ts")]
        self.assertTrue(vue and ts)
        for rel in vue:
            body = text(os.path.join(app, rel))
            if "<script" in body:
                self.assertTrue(body.startswith('<script setup lang="ts">\n'), rel)
            self.assertNotIn("[#", body, rel)
            self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,8}\b", body), rel)
            self.assertIsNone(palette.search(body), rel)
        for rel in ts:
            self.assertTrue(text(os.path.join(app, rel)).startswith("// "), rel)
        self.assertFalse(os.path.exists(os.path.join(app, "tailwind.config.js")))


if __name__ == "__main__":
    unittest.main()
