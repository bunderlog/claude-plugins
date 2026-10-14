# cspell:ignore AKIA IOSFODNN xoxb

import os
import unittest

from baloo.checks import Error, mask_secrets, no_secrets_in_commits
from tests import testkit
from tests.checks import stage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# A fake Secret of each kind, built at run time, so this file holds none and passes the Check
# itself.
SECRETS = [
    ("a private key", "-----BEGIN RSA " + "PRIVATE KEY-----"),
    ("a private key", "-----BEGIN " + "PRIVATE KEY-----"),
    ("an AWS access key", "AKIA" + "IOSFODNN7EXAMPLE"),
    ("a GitHub token", "ghp_" + "a1" * 18),
    ("a GitHub token", "github_pat_" + "A_b1" * 16),
    ("a Slack token", "xoxb-" + "1234567890-abc"),
    ("a Stripe live key", "sk_live_" + "a1B2" * 6),
    ("an Anthropic API key", "sk-ant-" + "api03-" * 4),
    ("an OpenAI API key", "sk-proj-" + "a1B2" * 6),
    ("a Google API key", "AIza" + "Sy" * 17 + "x"),
    ("a JWT", "eyJ" + "hbGciOiJIUzI1NiJ9.eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0." + "Sf" * 20),
    ("a password in a URL", "ftp://dm:" + "hunter2-Pass" + "@10.0.0.1/devices"),
    ("a password in a URL", "redis://:" + "hunter2" + "@cache:6379"),
]
AWS = SECRETS[2][1]
UNMARKED = ": an env file; keep it out of git, or put baloo:allow-secret on its first line"


class NoSecretsInCommits(unittest.TestCase):
    def test_finds_each_kind(self):
        for what, secret in SECRETS:
            with self.subTest(what=what, secret=secret[:12]):
                dir = testkit.repo(self)
                stage(dir, {"src/a.go": f'x := 1\nkey := "{secret}"\n'})
                self.assertEqual(no_secrets_in_commits(dir), ["src/a.go:2: " + what])

    def test_passes_what_is_no_secret(self):
        dir = testkit.repo(self)
        lines = [
            "sk-learn is a library",
            "re := regexp.MustCompile(`AKIA[0-9A-Z]{16}`)",
            "-----BEGIN PUBLIC KEY-----",
            "ghp_short",
            "sk_test_" + "a1B2" * 6,
            "eyJhbGciOiJIUzI1NiJ9 alone",
            "postgres://user:${DB_PASSWORD}@db/app",
            "https://x:$TOKEN@github.com/org/repo",
            "https://<user>:<password>@host",
            "https://user:****@host",
            "https://user@host:8080/path",
            "http://localhost:8080/a@b",
            "git@github.com:org/repo.git",
        ]
        stage(dir, {"a.go": "\n".join(lines)})
        self.assertEqual(no_secrets_in_commits(dir), [])

    def test_never_reports_the_secret(self):
        dir = testkit.repo(self)
        stage(dir, {"a.go": AWS})
        self.assertNotIn(AWS, "\n".join(no_secrets_in_commits(dir)))

    def test_passes_a_line_marked_allow_secret(self):
        dir = testkit.repo(self)
        stage(dir, {"a.go": f"{AWS} // baloo:allow-secret\n{AWS}\n"})
        self.assertEqual(no_secrets_in_commits(dir), ["a.go:2: an AWS access key"])

    # Only lines the staged changes add count, by their line in the staged file.
    def test_finds_only_added_lines(self):
        dir = testkit.repo(self)
        lines = ("ok\n" * 12).split("\n")
        lines[2] = AWS
        stage(dir, {"a.go": "\n".join(lines)})
        testkit.git(dir, "commit", "-qm", "x")
        lines[2] = "ok"
        lines[10] = "++ " + AWS  # an added line that looks like a diff's header
        stage(dir, {"a.go": "\n".join(lines)})
        with open(os.path.join(dir, "unstaged.go"), "w") as f:
            f.write(AWS)
        self.assertEqual(no_secrets_in_commits(dir), ["a.go:11: an AWS access key"])
        testkit.git(dir, "commit", "-qm", "y")
        testkit.git(dir, "rm", "-q", "a.go")
        self.assertEqual(no_secrets_in_commits(dir), [])

    def test_finds_env_files_but_not_their_templates(self):
        dir = testkit.repo(self)
        paths = [
            ".env", "app/.env.local", "prod.env", ".envrc", ".env.example", "a.env.sample", "env.go"
        ]
        stage(dir, {path: "" for path in paths})
        self.assertEqual(
            no_secrets_in_commits(dir),
            [p + UNMARKED for p in [".env", ".envrc", "app/.env.local", "prod.env"]],
        )

    # An Env file marked on its first line passes, and its lines are still looked through.
    def test_passes_an_env_file_marked_on_its_first_line(self):
        dir = testkit.repo(self)
        stage(
            dir,
            {
                ".env": "# public defaults, baloo:allow-secret\nPORT=3000\n",
                "b.env": "PORT=3000\n# baloo:allow-secret\n",
            },
        )
        self.assertEqual(no_secrets_in_commits(dir), ["b.env" + UNMARKED])
        stage(dir, {".env": f"# baloo:allow-secret\nKEY={AWS}\n"})
        self.assertIn(".env:2: an AWS access key", no_secrets_in_commits(dir))

    # The Check's own files hold no Secret, so a repo that commits them passes.
    def test_passes_its_own_files(self):
        dir = testkit.repo(self)
        files = {}
        for path in [
            os.path.join(ROOT, "plugins", "baloo", "scripts", "baloo", "checks", "secrets.py"),
            os.path.join(HERE, "test_secrets.py"),
        ]:
            with open(path) as f:
                files[os.path.basename(path)] = f.read()
        stage(dir, files)
        self.assertEqual(no_secrets_in_commits(dir), [])

    def test_fails_outside_a_repo(self):
        testkit.repo(self)  # for its environment
        with self.assertRaises(Error):
            no_secrets_in_commits(testkit.tempdir(self))


class MaskSecrets(unittest.TestCase):
    def test_masks_each_secret_and_nothing_else(self):
        self.assertEqual(mask_secrets(f"key = {AWS}; x = 1", "***"), "key = ***; x = 1")
        url = SECRETS[11][1]
        self.assertEqual(mask_secrets(url, "***"), "***10.0.0.1/devices")


if __name__ == "__main__":
    unittest.main()
