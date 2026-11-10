import unittest

from bagheera.checks import mask_secrets
from bagheera.checks.secrets import is_env_file

# A fake Secret of each kind, built at run time, so this file holds none and passes a commit's
# Secrets check.
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


class MaskSecrets(unittest.TestCase):
    def test_masks_each_secret_and_nothing_else(self):
        self.assertEqual(mask_secrets(f"key = {AWS}; x = 1", "***"), "key = ***; x = 1")
        url = SECRETS[11][1]
        self.assertEqual(mask_secrets(url, "***"), "***10.0.0.1/devices")

    def test_masks_each_kind(self):
        for what, secret in SECRETS:
            with self.subTest(what=what):
                self.assertNotIn(secret, mask_secrets(f"x = {secret}\n", "***"))


class IsEnvFile(unittest.TestCase):
    def test_tells_env_files_from_their_templates(self):
        for path in [".env", "app/.env.local", "prod.env", ".envrc"]:
            self.assertTrue(is_env_file(path), path)
        for path in [".env.example", "app/.env.sample", ".env.template", "x.env.dist", "env.md"]:
            self.assertFalse(is_env_file(path), path)


if __name__ == "__main__":
    unittest.main()
