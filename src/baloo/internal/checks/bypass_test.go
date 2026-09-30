package checks

import "testing"

func TestNoGitHookBypass_DeniesABypass(t *testing.T) {
	for command, want := range map[string]string{
		"git commit --no-verify -m x":                 "git commit --no-verify bypasses the Git hooks",
		"git commit -n -m x":                          "git commit --no-verify bypasses the Git hooks",
		"git commit -anm x":                           "git commit --no-verify bypasses the Git hooks",
		"git push --no-verify":                        "git push --no-verify bypasses the Git hooks",
		"git merge --no-verify feature":               "git merge --no-verify bypasses the Git hooks",
		"git -C src commit --no-verify":               "git commit --no-verify bypasses the Git hooks",
		"git --git-dir .git commit --no-verify":       "git commit --no-verify bypasses the Git hooks",
		"/usr/bin/git commit --no-verify":             "git commit --no-verify bypasses the Git hooks",
		"git -c core.hooksPath=/dev/null commit -m x": "git -c core.hooksPath=… bypasses the Git hooks",
		"git -c core.hookspath=/dev/null push":        "git -c core.hooksPath=… bypasses the Git hooks",
		"git config core.hooksPath /dev/null":         "git config core.hooksPath changes where the Git hooks are",
		"git config --local core.hooksPath x":         "git config core.hooksPath changes where the Git hooks are",
		"git config set core.hooksPath x":             "git config core.hooksPath changes where the Git hooks are",
		"git config --unset core.hooksPath":           "git config core.hooksPath changes where the Git hooks are",
		"git config unset core.hooksPath":             "git config core.hooksPath changes where the Git hooks are",
		"HUSKY=0 git commit -m x":                     "HUSKY=0 turns the Git hooks off",
		"env HUSKY=0 git push":                        "HUSKY=0 turns the Git hooks off",
		"export HUSKY=0":                              "HUSKY=0 turns the Git hooks off",
		`cd src && git commit -m "a; b" --no-verify`:  "git commit --no-verify bypasses the Git hooks",
		"make && git push --no-verify | cat":          "git push --no-verify bypasses the Git hooks",
		`bash -c "git commit --no-verify"`:            "git commit --no-verify bypasses the Git hooks",
		"eval git commit --no-verify":                 "git commit --no-verify bypasses the Git hooks",
		"sudo -u me git commit --no-verify":           "git commit --no-verify bypasses the Git hooks",
		"echo $(git commit --no-verify)":              "git commit --no-verify bypasses the Git hooks",
		"git commit --no-verify\ngit push":            "git commit --no-verify bypasses the Git hooks",
		`git commit -m 'x' \` + "\n" + ` --no-verify`: "git commit --no-verify bypasses the Git hooks",
	} {
		if got := NoGitHookBypass(command); got != want {
			t.Errorf("NoGitHookBypass(%q) = %q, want %q", command, got, want)
		}
	}
}

func TestNoGitHookBypass_AllowsWhatBypassesNothing(t *testing.T) {
	for _, command := range []string{
		"git commit -m x",
		"git commit -m 'skip it with --no-verify'",
		`git commit -m "HUSKY=0"`,
		"echo git commit --no-verify",
		"git clean -n",
		"git add -n .",
		"git config core.hooksPath",
		"git config --get core.hooksPath",
		"git config get core.hooksPath",
		"git config --list",
		"git config user.name me",
		"git -c user.name=me commit -m x",
		"HUSKY=1 git commit -m x",
		"grep -r no-verify .",
		"",
	} {
		if got := NoGitHookBypass(command); got != "" {
			t.Errorf("NoGitHookBypass(%q) = %q, want none", command, got)
		}
	}
}
