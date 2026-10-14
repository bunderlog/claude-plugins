# cspell:ignore netrc pipefail typeset

import json
import os
import unittest

from baloo.checks import ALLOW_SECRET, no_secrets_in_context
from tests import testkit

LEAK_ADVICE = (
    ": showing it would put a secret into this session. If it's really needed, ask the user to "
    "look in their own terminal, not with `!`, whose output enters the session."
)


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


class NoSecretsInContext(unittest.TestCase):
    def setUp(self):
        """A folder with an unmarked Env file and one marked as holding no Secret."""
        self.dir = testkit.tempdir(self)
        for name, text in {
            ".env": "API_KEY=x\n",
            "public.env": f"# defaults, {ALLOW_SECRET}\nPORT=3000\n",
        }.items():
            with open(os.path.join(self.dir, name), "w") as f:
                f.write(text)

    def test_denies_a_command_that_shows_a_secret(self):
        env = "env prints every environment variable"
        printenv = "printenv prints every environment variable"
        for command, what in {
            "cat .env": ".env is an env file",
            "head -n 5 app/.env.local": "app/.env.local is an env file",
            "grep KEY .env": ".env is an env file",
            "cat .envrc": ".envrc is an env file",
            "grep -e x -- .env": ".env is an env file",
            "while read l; do echo $l; done < .env": ".env is an env file",
            "sort <.env": ".env is an env file",
            "less ~/.ssh/id_ed25519": "~/.ssh/id_ed25519 holds a private key",
            "cat server.pem": "server.pem holds a private key",
            "cat ~/.aws/credentials": "~/.aws/credentials holds secrets",
            "cat $HOME/.netrc": "$HOME/.netrc holds secrets",
            "bash -c 'cat .env'": ".env is an env file",
            "env": env,
            "env -0": env,
            "env | grep TOKEN": env,
            "env; cut -d= -f1 names": env,
            "env || cut -d= -f1": env,
            "env | cut -d= -f2": env,
            "env | grep -o '^.*'": env,
            "env | sed 's/=.*/&/'": env,
            "env | awk -F= '{print $2}'": env,
            "cat <<EOF\nx\nEOF\nenv": env,  # cspell:disable-line
            "bash <<EOF\nenv\nEOF": env,  # cspell:disable-line
            "sudo sh -s <<'EOF'\nprintenv\nEOF": printenv,
            "cat <<-'EOF' >f\n\tset\n\tEOF\nprintenv": printenv,
            "printenv": printenv,
            "printenv GITHUB_TOKEN": "printenv GITHUB_TOKEN prints a secret",
            "export": "export prints every exported variable",
            "export -p": "export prints every exported variable",
            "declare -p DB_PASSWORD": "declare -p DB_PASSWORD prints a secret",
            "set": "set prints every shell variable",
            "env | grep -o '^A\\|B[A-Z]*'": env,
            "env | grep -oE '^A|[A-Z]*'": env,
            "echo $OPENAI_API_KEY": "echo $OPENAI_API_KEY prints a secret",
            'echo "${GH_TOKEN:-none}"': "echo $GH_TOKEN prints a secret",
            'echo "${X:+$GH_TOKEN}"': "echo $GH_TOKEN prints a secret",
            'echo "${GH_TOKEN_X:+set}" $GH_TOKEN': "echo $GH_TOKEN prints a secret",
            'echo "id: $(echo $GH_TOKEN)"': "echo $GH_TOKEN prints a secret",
            'echo "$(cat .env)"': ".env is an env file",
            'echo "token: ${GH_TOKEN}"': "echo $GH_TOKEN prints a secret",
            "printf '%s' $STRIPE_SECRET": "printf $STRIPE_SECRET prints a secret",
            "gh auth token": "gh auth token prints a secret",
            "gh auth status --show-token": "gh auth token prints a secret",
            "security find-generic-password -s x -w": "security find-generic-password -w prints a password",
            "aws configure get aws_secret_access_key": "aws configure get prints a secret",
            "aws configure export-credentials": "aws configure export-credentials prints a secret",
            "op read op://vault/item/password": "op read prints a secret",
            "git credential fill": "git credential fill prints a secret",
        }.items():
            with self.subTest(command=command):
                self.assertEqual(no_secrets_in_context(bash(command), self.dir), what + LEAK_ADVICE)

    def test_allows_a_command_that_shows_none(self):
        for command in [
            """grep -n '"prod.env", ".env.example"' src/a.go""",
            "env | cut -d= -f1",
            "python3 - <<'EOF'\nprint(sorted(set(words)))\nenv = 1\nEOF",  # cspell:disable-line
            "cat <<EOF > notes.txt\nset\nenv\nEOF\necho done",  # cspell:disable-line
            "cat <<< 'here-string' | wc -c",
            "env | sort | cut -d '=' -f 1",
            "env | grep -oE '^(BITBUCKET|JIRA)[A-Z_]*'",
            "env | grep -i -o '^[A-Z_]*BITBUCKET[A-Z_]*\\|^ATLASSIAN[A-Z_]*' | sort -u",
            "env | grep -oE '^BITBUCKET[A-Z_]*|^JIRA[A-Z_]*'",
            'echo "${JIRA_EMAIL:+set} ${ATLASSIAN_API_TOKEN:+set}"',
            'echo "$t: $(curl -s -o /dev/null -w \'%{http_code}\' -u "$JIRA_EMAIL:$ATLASSIAN_API_TOKEN" $J)"',
            "env | grep TOKEN | sed 's/=.*/=<set>/'",
            "printenv | awk -F= '{print $1}'",
            "rg 'x.env' src",
            "cat .env.example",
            "cat public.env",
            "cp .env .env.bak",
            "rm .env",
            "cat ~/.ssh/id_ed25519.pub",
            "env FOO=1 go test",
            "printenv HOME",
            "export FOO=1",
            "set -euo pipefail",
            "echo $HOME $PATH $SSH_AUTH_SOCK",
            "gh auth status",
            "aws configure get region",
            "git status",
            "echo '" + 'KEY = "example" // ' + ALLOW_SECRET + "' >> src/a.go",
            "",
        ]:
            with self.subTest(command=command):
                self.assertEqual(no_secrets_in_context(bash(command), self.dir), "")

    # Read and Grep show a file as cat and grep do.
    def test_denies_reading_a_secret_file(self):
        for given, what in [
            ({"tool_name": "Read", "tool_input": {"file_path": "/srv/app/.env"}}, "/srv/app/.env is an env file"),
            ({"tool_name": "Read", "tool_input": {"file_path": ".env"}}, ".env is an env file"),
            ({"tool_name": "Grep", "tool_input": {"pattern": "x", "glob": "*.pem"}}, "*.pem holds a private key"),
            (
                {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "~/.aws/credentials"}},
                "~/.aws/credentials holds secrets",
            ),
        ]:
            with self.subTest(call=given):
                self.assertEqual(no_secrets_in_context(given, self.dir), what + LEAK_ADVICE)
        for given in [
            {"tool_name": "Read", "tool_input": {"file_path": "src/env.go"}},
            {"tool_name": "Read", "tool_input": {"file_path": "public.env"}},
            {"tool_name": "Read", "tool_input": {"file_path": "id_rsa.pub"}},
            {"tool_name": "Grep", "tool_input": {"pattern": ".env", "path": "src"}},
        ]:
            with self.subTest(call=given):
                self.assertEqual(no_secrets_in_context(given, self.dir), "")

    # Only the user marks an Env file as holding no Secret, whatever tool Claude would mark it with.
    def test_denies_marking_an_env_file(self):
        want = (
            f"only the user marks an env file as holding no secrets ({ALLOW_SECRET}). If it "
            "really holds none, ask the user to mark it themselves."
        )
        for given in [
            bash(f"sed -i '' '1i\\\n# {ALLOW_SECRET}' .env"),
            bash(f"echo '# {ALLOW_SECRET}' | cat - app/.env.local > t && mv t app/.env.local"),
            bash(f"printf '# {ALLOW_SECRET}\\n' >>prod.env"),
            {"tool_name": "Write", "tool_input": {"file_path": "/srv/.env", "content": f"# {ALLOW_SECRET}\nX=1\n"}},
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": ".env", "old_string": "A", "new_string": f"# {ALLOW_SECRET}\nA"},
            },
            {
                "tool_name": "MultiEdit",
                "tool_input": {"file_path": ".env", "edits": [{"new_string": "x"}, {"new_string": ALLOW_SECRET}]},
            },
        ]:
            with self.subTest(call=given):
                self.assertEqual(no_secrets_in_context(given, self.dir), want)
        for given in [
            {"tool_name": "Write", "tool_input": {"file_path": ".env.example", "content": f"# {ALLOW_SECRET}"}},
            {"tool_name": "Edit", "tool_input": {"file_path": "src/a.go", "new_string": f"// {ALLOW_SECRET}"}},
            {"tool_name": "Edit", "tool_input": {"file_path": ".env", "new_string": "PORT=3000"}},
        ]:
            with self.subTest(call=given):
                self.assertEqual(no_secrets_in_context(given, self.dir), "")

    # An Env file that can't be read, such as a folder of that name, counts as unmarked.
    def test_counts_an_unreadable_env_file_as_unmarked(self):
        dir = testkit.tempdir(self)
        os.mkdir(os.path.join(dir, ".env"))
        self.assertTrue(no_secrets_in_context(bash("cat .env"), dir).startswith(".env is an env file"))

    # A tool input of another shape than Claude Code's, such as a command that isn't a string, shows
    # nothing.
    def test_takes_a_tool_input_of_another_shape_for_none(self):
        for given in [{}, {"tool_name": "Bash"}, json.loads('{"tool_name": "Bash", "tool_input": {"command": 1}}')]:
            with self.subTest(call=given):
                self.assertEqual(no_secrets_in_context(given, self.dir), "")


if __name__ == "__main__":
    unittest.main()
