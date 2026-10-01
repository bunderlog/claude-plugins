package checks

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// cspell:ignore netrc pipefail typeset

// project is a folder with an unmarked Env file and one marked as holding no Secret.
func project(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	for name, text := range map[string]string{
		".env":       "API_KEY=x\n",
		"public.env": "# defaults, " + AllowSecret + "\nPORT=3000\n",
	} {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return dir
}

// call is the tool call Claude Code gives a PreToolUse hook as `in`, a JSON object.
func call(t *testing.T, in string) ToolCall {
	t.Helper()
	var c ToolCall
	if err := json.Unmarshal([]byte(in), &c); err != nil {
		t.Fatal(err)
	}
	return c
}

func bash(t *testing.T, command string) ToolCall {
	t.Helper()
	in, _ := json.Marshal(map[string]any{"tool_name": "Bash", "tool_input": map[string]string{"command": command}})
	return call(t, string(in))
}

const leakAdvice = ": showing it would put a secret into this session. If it's really needed, ask the " +
	"user to look in their own terminal, not with `!`, whose output enters the session."

func TestNoSecretsInContext_DeniesACommandThatShowsASecret(t *testing.T) {
	dir := project(t)
	for command, what := range map[string]string{
		"cat .env":                                ".env is an env file",
		"head -n 5 app/.env.local":                "app/.env.local is an env file",
		"grep KEY .env":                           ".env is an env file",
		"cat .envrc":                              ".envrc is an env file",
		"grep -e x -- .env":                       ".env is an env file",
		"while read l; do echo $l; done < .env":   ".env is an env file",
		"sort <.env":                              ".env is an env file",
		"less ~/.ssh/id_ed25519":                  "~/.ssh/id_ed25519 holds a private key",
		"cat server.pem":                          "server.pem holds a private key",
		"cat ~/.aws/credentials":                  "~/.aws/credentials holds secrets",
		"cat $HOME/.netrc":                        "$HOME/.netrc holds secrets",
		"bash -c 'cat .env'":                      ".env is an env file",
		"env":                                     "env prints every environment variable",
		"env -0":                                  "env prints every environment variable",
		"env | grep TOKEN":                        "env prints every environment variable",
		"env; cut -d= -f1 names":                  "env prints every environment variable",
		"env || cut -d= -f1":                      "env prints every environment variable",
		"env | cut -d= -f2":                       "env prints every environment variable",
		"env | grep -o '^.*'":                     "env prints every environment variable",
		"env | sed 's/=.*/&/'":                    "env prints every environment variable",
		"env | awk -F= '{print $2}'":              "env prints every environment variable",
		"printenv":                                "printenv prints every environment variable",
		"printenv GITHUB_TOKEN":                   "printenv GITHUB_TOKEN prints a secret",
		"export":                                  "export prints every exported variable",
		"export -p":                               "export prints every exported variable",
		"declare -p DB_PASSWORD":                  "declare -p DB_PASSWORD prints a secret",
		"set":                                     "set prints every shell variable",
		"echo $OPENAI_API_KEY":                    "echo $OPENAI_API_KEY prints a secret",
		`echo "token: ${GH_TOKEN}"`:               "echo $GH_TOKEN prints a secret",
		"printf '%s' $STRIPE_SECRET":              "printf $STRIPE_SECRET prints a secret",
		"gh auth token":                           "gh auth token prints a secret",
		"gh auth status --show-token":             "gh auth token prints a secret",
		"security find-generic-password -s x -w":  "security find-generic-password -w prints a password",
		"aws configure get aws_secret_access_key": "aws configure get prints a secret",
		"aws configure export-credentials":        "aws configure export-credentials prints a secret",
		"op read op://vault/item/password":        "op read prints a secret",
		"git credential fill":                     "git credential fill prints a secret",
	} {
		if got, want := NoSecretsInContext(bash(t, command), dir), what+leakAdvice; got != want {
			t.Errorf("NoSecretsInContext(%q) = %q, want %q", command, got, want)
		}
	}
}

func TestNoSecretsInContext_AllowsACommandThatShowsNone(t *testing.T) {
	dir := project(t)
	for _, command := range []string{
		`grep -n '"prod.env", ".env.example"' src/a.go`,
		"env | cut -d= -f1",
		"env | sort | cut -d '=' -f 1",
		"env | grep -oE '^(BITBUCKET|JIRA)[A-Z_]*'",
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
		"echo '" + `KEY = "example" // ` + AllowSecret + "' >> src/a.go",
		"",
	} {
		if got := NoSecretsInContext(bash(t, command), dir); got != "" {
			t.Errorf("NoSecretsInContext(%q) = %q, want none", command, got)
		}
	}
}

// Read and Grep show a file as cat and grep do.
func TestNoSecretsInContext_DeniesReadingASecretFile(t *testing.T) {
	dir := project(t)
	for in, what := range map[string]string{
		`{"tool_name": "Read", "tool_input": {"file_path": "/srv/app/.env"}}`:                 "/srv/app/.env is an env file",
		`{"tool_name": "Read", "tool_input": {"file_path": ".env"}}`:                          ".env is an env file",
		`{"tool_name": "Grep", "tool_input": {"pattern": "x", "glob": "*.pem"}}`:              "*.pem holds a private key",
		`{"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "~/.aws/credentials"}}`: "~/.aws/credentials holds secrets",
	} {
		if got, want := NoSecretsInContext(call(t, in), dir), what+leakAdvice; got != want {
			t.Errorf("NoSecretsInContext(%s) = %q, want %q", in, got, want)
		}
	}
	for _, in := range []string{
		`{"tool_name": "Read", "tool_input": {"file_path": "src/env.go"}}`,
		`{"tool_name": "Read", "tool_input": {"file_path": "public.env"}}`,
		`{"tool_name": "Read", "tool_input": {"file_path": "id_rsa.pub"}}`,
		`{"tool_name": "Grep", "tool_input": {"pattern": ".env", "path": "src"}}`,
	} {
		if got := NoSecretsInContext(call(t, in), dir); got != "" {
			t.Errorf("NoSecretsInContext(%s) = %q, want none", in, got)
		}
	}
}

// Only the user marks an Env file as holding no Secret, whatever tool Claude would mark it with.
func TestNoSecretsInContext_DeniesMarkingAnEnvFile(t *testing.T) {
	dir := project(t)
	want := "only the user marks an env file as holding no secrets (" + AllowSecret + "). If it " +
		"really holds none, ask the user to mark it themselves."
	for _, c := range []ToolCall{
		bash(t, "sed -i '' '1i\\\n# "+AllowSecret+"' .env"),
		bash(t, "echo '# "+AllowSecret+"' | cat - app/.env.local > t && mv t app/.env.local"),
		bash(t, "printf '# "+AllowSecret+"\\n' >>prod.env"),
		call(t, `{"tool_name": "Write", "tool_input": {"file_path": "/srv/.env", "content": "# `+AllowSecret+`\nX=1\n"}}`),
		call(t, `{"tool_name": "Edit", "tool_input": {"file_path": ".env", "old_string": "A", "new_string": "# `+AllowSecret+`\nA"}}`),
		call(t, `{"tool_name": "MultiEdit", "tool_input": {"file_path": ".env", "edits": [{"new_string": "x"}, {"new_string": "`+AllowSecret+`"}]}}`),
	} {
		if got := NoSecretsInContext(c, dir); got != want {
			t.Errorf("NoSecretsInContext(%+v) = %q, want %q", c, got, want)
		}
	}
	for _, in := range []string{
		`{"tool_name": "Write", "tool_input": {"file_path": ".env.example", "content": "# ` + AllowSecret + `"}}`,
		`{"tool_name": "Edit", "tool_input": {"file_path": "src/a.go", "new_string": "// ` + AllowSecret + `"}}`,
		`{"tool_name": "Edit", "tool_input": {"file_path": ".env", "new_string": "PORT=3000"}}`,
	} {
		if got := NoSecretsInContext(call(t, in), dir); got != "" {
			t.Errorf("NoSecretsInContext(%s) = %q, want none", in, got)
		}
	}
}

// An Env file that can't be read, such as a folder of that name, counts as unmarked.
func TestNoSecretsInContext_CountsAnUnreadableEnvFileAsUnmarked(t *testing.T) {
	dir := t.TempDir()
	if err := os.Mkdir(filepath.Join(dir, ".env"), 0o755); err != nil {
		t.Fatal(err)
	}
	if got := NoSecretsInContext(bash(t, "cat .env"), dir); !strings.HasPrefix(got, ".env is an env file") {
		t.Errorf("NoSecretsInContext = %q, want the env file denied", got)
	}
}
