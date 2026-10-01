package checks

// cspell:ignore nvme

import (
	"path/filepath"
	"regexp"
	"slices"
	"strings"
)

var (
	forkBomb = regexp.MustCompile(`:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:`)
	// pipedDownload is a download piped into a shell, which runs code nobody has read.
	pipedDownload = regexp.MustCompile(`\b(curl|wget)\b[^|;&]*\|\s*(sudo\s+)?(ba|z|da)?sh\b`)
	rawDisk       = regexp.MustCompile(`>\s*/dev/(sd|disk|nvme|hd)`)
	diskErase     = regexp.MustCompile(`(?i)^(erase|zero|randomize|secureErase|partitionDisk)`)
)

// everything are the paths that stand for every file below them: rm -r on one deletes it all.
var everything = []string{"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", "$HOME/*", ".", "./",
	"./*", "..", "../", "*"}

// NoDestructiveCommands is the Check baloo:no-destructive-commands (PreToolUse on Bash): why the
// shell command `command`, run in the folder `dir`, would destroy work beyond undo, for Claude
// Code to deny it; or else why the user should say first, for it to ask them; or neither. It asks
// where the user often asks for the command by name (`git push --delete` of a branch the remote's
// default branch doesn't hold), and before reset --hard on a tree with no changes to lose, which
// only moves the branch.
func NoDestructiveCommands(command, dir string) (deny, ask string) {
	switch {
	case forkBomb.MatchString(command):
		return "a fork bomb exhausts the machine", ""
	case pipedDownload.MatchString(command):
		return "piping a download into a shell runs code nobody has read", ""
	case rawDisk.MatchString(command):
		return "writing to a raw disk device erases it", ""
	}
	for _, p := range programs(command) {
		why, asks := destroys(p, dir)
		if why != "" && !asks {
			return why, ""
		}
		if ask == "" {
			ask = why
		}
	}
	return "", ask
}

// destroys is why the program `p`, run in `dir`, would destroy work, and whether the user should
// be asked rather than the program denied.
func destroys(p program, dir string) (why string, ask bool) {
	args := p.args
	switch p.name {
	case "git":
		return gitDestroys(args, dir)
	case "rm":
		if slices.Contains(args, "--no-preserve-root") {
			return "rm --no-preserve-root deletes /", false
		}
		if hasFlag(args, "-r", "-R", "--recursive") && slices.ContainsFunc(args, isEverything) {
			return "rm -r on /, ~, . or * deletes everything below it", false
		}
		if hasFlag(args, "-r", "-R", "--recursive") && slices.ContainsFunc(args, isGitFolder) {
			return "rm -r on .git deletes the repo's history", false
		}
	case "dd":
		if slices.ContainsFunc(args, func(a string) bool { return strings.HasPrefix(a, "of=/dev/") }) {
			return "dd onto a device erases a disk", false
		}
	case "diskutil":
		if len(args) > 0 && diskErase.MatchString(args[0]) {
			return "diskutil " + args[0] + " erases a disk", false
		}
	case "chmod", "chown":
		if hasFlag(args, "-R") && slices.ContainsFunc(args, isEverything) {
			return p.name + " -R on /, ~ or . changes every file below it", false
		}
	}
	if strings.HasPrefix(p.name, "mkfs") {
		return p.name + " formats a disk", false
	}
	return "", false
}

func isEverything(a string) bool { return slices.Contains(everything, a) }

// isGitFolder says whether the path `a` is a repo's .git folder.
func isGitFolder(a string) bool { return filepath.Base(a) == ".git" }

// gitDestroys is destroys for git with the arguments `args`.
func gitDestroys(args []string, dir string) (why string, ask bool) {
	options, sub, rest := splitGit(args)
	var paths []string
	for _, a := range rest {
		if !strings.HasPrefix(a, "-") {
			paths = append(paths, a)
		}
	}
	switch sub {
	case "push":
		if hasFlag(rest, "--force", "-f", "--mirror") ||
			slices.ContainsFunc(paths, func(a string) bool { return strings.HasPrefix(a, "+") }) {
			return "git push --force rewrites remote history; --force-with-lease is allowed", false
		}
		remote, branches := deletes(rest, paths)
		if (hasFlag(rest, "--delete", "-d") || branches != nil) &&
			!merged(gitFolder(dir, options), remote, branches) {
			return "git push --delete removes a remote branch", true
		}
	case "reset":
		if hasFlag(rest, "--merge") {
			return "git reset --merge discards changes", false
		}
		if hasFlag(rest, "--hard") {
			if clean(gitFolder(dir, options)) {
				return "git reset --hard moves the branch; the tree has no changes to lose", true
			}
			return "git reset --hard discards changes", false
		}
	case "clean":
		if hasFlag(rest, "--force", "-f") {
			return "git clean -f deletes untracked files", false
		}
	case "checkout":
		if slices.Contains(rest, "--") {
			return "git checkout -- discards uncommitted changes to tracked files", false
		}
		if hasFlag(rest, "--force", "-f") || slices.Contains(paths, ".") {
			return "git checkout . / -f discards uncommitted changes", false
		}
	case "restore":
		// --staged alone only takes files out of the index; the working tree is restored by
		// default, or with --worktree.
		if !hasFlag(rest, "--staged", "-S") || hasFlag(rest, "--worktree", "-W") {
			return "git restore discards uncommitted changes to tracked files", false
		}
	case "switch":
		if hasFlag(rest, "--discard-changes", "--force", "-f") {
			return "git switch --discard-changes discards uncommitted changes", false
		}
	case "branch":
		if hasFlag(rest, "-D") || hasFlag(rest, "--delete", "-d") && hasFlag(rest, "--force", "-f") {
			return "git branch -D deletes an unmerged branch", false
		}
	case "stash":
		if len(rest) > 0 && (rest[0] == "drop" || rest[0] == "clear") {
			return "git stash drop/clear loses stashes", false
		}
	case "reflog":
		if len(rest) > 0 && (rest[0] == "expire" || rest[0] == "delete") {
			return "git reflog expire loses history", false
		}
	case "gc":
		if hasFlag(rest, "--prune=now", "--prune=all") {
			return "git gc --prune=now deletes unreachable commits at once", false
		}
	case "prune":
		if !hasFlag(rest, "--dry-run", "-n") &&
			!slices.ContainsFunc(rest, func(a string) bool { return strings.HasPrefix(a, "--expire") }) {
			return "git prune deletes unreachable commits at once", false
		}
	case "update-ref":
		if hasFlag(rest, "-d") {
			return "git update-ref -d deletes a branch, merged or not", false
		}
	case "filter-branch", "filter-repo":
		return "git " + sub + " rewrites the whole history", false
	}
	return "", false
}

// deletes is the remote and the branches there that git push with the arguments `rest`, of
// which `paths` are the ones not flags, deletes; no branches where it deletes none, and no remote
// where the command names none.
func deletes(rest, paths []string) (remote string, branches []string) {
	if hasFlag(rest, "--delete", "-d") {
		if len(paths) == 0 {
			return "", nil
		}
		return paths[0], paths[1:]
	}
	for _, a := range paths {
		if branch, ok := strings.CutPrefix(a, ":"); ok {
			branches = append(branches, branch)
		}
	}
	if len(paths) > 0 && !strings.HasPrefix(paths[0], ":") {
		remote = paths[0]
	}
	return remote, branches
}

// merged says whether the default branch of `remote`, as the repo at `dir` last fetched it,
// holds each of its `branches` whole; false where it can't say.
func merged(dir, remote string, branches []string) bool {
	head, err := git(dir, "symbolic-ref", "--quiet", "refs/remotes/"+remote+"/HEAD")
	if remote == "" || err != nil {
		return false
	}
	for _, branch := range branches {
		ref := "refs/remotes/" + remote + "/" + strings.TrimPrefix(branch, "refs/heads/")
		if _, err := git(dir, "merge-base", "--is-ancestor", ref, strings.TrimSpace(head)); err != nil {
			return false
		}
	}
	return true
}

// gitFolder is the folder git started in `dir` runs in, after the -C of its options `options`.
func gitFolder(dir string, options []string) string {
	for i, option := range options {
		if option == "-C" && i+1 < len(options) {
			if filepath.IsAbs(options[i+1]) {
				dir = options[i+1]
			} else {
				dir = filepath.Join(dir, options[i+1])
			}
		}
	}
	return dir
}

// clean says whether the working tree at `dir` has no change to a tracked file, staged or not;
// false where git can't say, such as outside a repo.
func clean(dir string) bool {
	changes, err := git(dir, "status", "--porcelain", "--untracked-files=no")
	return err == nil && changes == ""
}
