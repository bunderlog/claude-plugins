package checks

// cspell:ignore AKIA IOSFODNN xoxb

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"github.com/bunderlog/claude-plugins/src/baloo/internal/testkit"
)

// secrets are a fake Secret of each kind, built at run time, so this file holds none and passes
// the Check itself.
var secrets = []struct{ what, secret string }{
	{"a private key", "-----BEGIN RSA " + "PRIVATE KEY-----"},
	{"a private key", "-----BEGIN " + "PRIVATE KEY-----"},
	{"an AWS access key", "AKIA" + "IOSFODNN7EXAMPLE"},
	{"a GitHub token", "ghp_" + strings.Repeat("a1", 18)},
	{"a GitHub token", "github_pat_" + strings.Repeat("A_b1", 16)},
	{"a Slack token", "xoxb-" + "1234567890-abc"},
	{"a Stripe live key", "sk_live_" + strings.Repeat("a1B2", 6)},
	{"an Anthropic API key", "sk-ant-" + strings.Repeat("api03-", 4)},
	{"an OpenAI API key", "sk-proj-" + strings.Repeat("a1B2", 6)},
	{"a Google API key", "AIza" + strings.Repeat("Sy", 17) + "x"},
}

var aws = secrets[2].secret

// stage writes each file of `files`, by its path from the repo `dir`, and stages it.
func stage(t *testing.T, dir string, files map[string]string) {
	t.Helper()
	for path, text := range files {
		full := filepath.Join(dir, path)
		if err := os.MkdirAll(filepath.Dir(full), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(full, []byte(text), 0o644); err != nil {
			t.Fatal(err)
		}
		testkit.Git(t, dir, "add", path)
	}
}

func noSecretsInCommits(t *testing.T, dir string) []string {
	t.Helper()
	found, err := NoSecretsInCommits(dir)
	if err != nil {
		t.Fatalf("NoSecretsInCommits: %v", err)
	}
	return found
}

func TestNoSecretsInCommits_FindsEachKind(t *testing.T) {
	for _, s := range secrets {
		t.Run(s.what, func(t *testing.T) {
			dir := testkit.Repo(t)
			stage(t, dir, map[string]string{"src/a.go": "x := 1\nkey := \"" + s.secret + "\"\n"})
			want := []string{"src/a.go:2: " + s.what}
			if got := noSecretsInCommits(t, dir); !slices.Equal(got, want) {
				t.Errorf("NoSecretsInCommits = %q, want %q", got, want)
			}
		})
	}
}

func TestNoSecretsInCommits_PassesWhatIsNoSecret(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a.go": strings.Join([]string{
		"sk-learn is a library",
		"re := regexp.MustCompile(`AKIA[0-9A-Z]{16}`)",
		"-----BEGIN PUBLIC KEY-----",
		"ghp_short",
		"sk_test_" + strings.Repeat("a1B2", 6),
	}, "\n")})
	if got := noSecretsInCommits(t, dir); got != nil {
		t.Errorf("NoSecretsInCommits = %q, want none", got)
	}
}

func TestNoSecretsInCommits_NeverReportsTheSecret(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a.go": aws})
	if got := strings.Join(noSecretsInCommits(t, dir), "\n"); strings.Contains(got, aws) {
		t.Errorf("NoSecretsInCommits = %q, which holds the secret", got)
	}
}

func TestNoSecretsInCommits_PassesALineMarkedAllowSecret(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{"a.go": aws + " // baloo:allow-secret\n" + aws + "\n"})
	want := []string{"a.go:2: an AWS access key"}
	if got := noSecretsInCommits(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoSecretsInCommits = %q, want %q", got, want)
	}
}

// Only lines the staged changes add count, by their line in the staged file.
func TestNoSecretsInCommits_FindsOnlyAddedLines(t *testing.T) {
	dir := testkit.Repo(t)
	lines := strings.Split(strings.Repeat("ok\n", 12), "\n")
	lines[2] = aws
	stage(t, dir, map[string]string{"a.go": strings.Join(lines, "\n")})
	testkit.Git(t, dir, "commit", "-qm", "x")
	lines[2] = "ok"
	lines[10] = "++ " + aws // an added line that looks like a diff's header
	stage(t, dir, map[string]string{"a.go": strings.Join(lines, "\n")})
	if err := os.WriteFile(filepath.Join(dir, "unstaged.go"), []byte(aws), 0o644); err != nil {
		t.Fatal(err)
	}
	want := []string{"a.go:11: an AWS access key"}
	if got := noSecretsInCommits(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoSecretsInCommits = %q, want %q", got, want)
	}
	testkit.Git(t, dir, "commit", "-qm", "y")
	testkit.Git(t, dir, "rm", "-q", "a.go")
	if got := noSecretsInCommits(t, dir); got != nil {
		t.Errorf("NoSecretsInCommits with the secret deleted = %q, want none", got)
	}
}

func TestNoSecretsInCommits_FindsEnvFilesButNotTheirTemplates(t *testing.T) {
	dir := testkit.Repo(t)
	files := map[string]string{}
	for _, path := range []string{".env", "app/.env.local", "prod.env", ".envrc", ".env.example",
		"a.env.sample", "env.go"} {
		files[path] = ""
	}
	stage(t, dir, files)
	var want []string
	for _, path := range []string{".env", ".envrc", "app/.env.local", "prod.env"} {
		want = append(want, path+": an env file; keep it out of git, or put baloo:allow-secret on its first line")
	}
	if got := noSecretsInCommits(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoSecretsInCommits = %q, want %q", got, want)
	}
}

// An Env file marked on its first line passes, and its lines are still looked through.
func TestNoSecretsInCommits_PassesAnEnvFileMarkedOnItsFirstLine(t *testing.T) {
	dir := testkit.Repo(t)
	stage(t, dir, map[string]string{
		".env":  "# public defaults, baloo:allow-secret\nPORT=3000\n",
		"b.env": "PORT=3000\n# baloo:allow-secret\n",
	})
	want := []string{"b.env: an env file; keep it out of git, or put baloo:allow-secret on its first line"}
	if got := noSecretsInCommits(t, dir); !slices.Equal(got, want) {
		t.Errorf("NoSecretsInCommits = %q, want %q", got, want)
	}
	stage(t, dir, map[string]string{".env": "# baloo:allow-secret\nKEY=" + aws + "\n"})
	if got := noSecretsInCommits(t, dir); !slices.Contains(got, ".env:2: an AWS access key") {
		t.Errorf("NoSecretsInCommits = %q, want the secret in .env found", got)
	}
}

// The Check's own files hold no Secret, so a repo that commits them passes.
func TestNoSecretsInCommits_PassesItsOwnFiles(t *testing.T) {
	dir := testkit.Repo(t)
	files := map[string]string{}
	for _, name := range []string{"secrets.go", "secrets_test.go"} {
		text, err := os.ReadFile(name)
		if err != nil {
			t.Fatal(err)
		}
		files[name] = string(text)
	}
	stage(t, dir, files)
	if got := noSecretsInCommits(t, dir); got != nil {
		t.Errorf("NoSecretsInCommits = %q, want none", got)
	}
}

func TestNoSecretsInCommits_FailsOutsideARepo(t *testing.T) {
	testkit.Repo(t) // for its environment
	if _, err := NoSecretsInCommits(t.TempDir()); err == nil {
		t.Error("NoSecretsInCommits outside a repo = no error, want one")
	}
}
