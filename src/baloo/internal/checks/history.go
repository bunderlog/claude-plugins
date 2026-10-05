package checks

import "strings"

// LinearHistory is the Check baloo:linear-history (pre-push): `<ref> <commit>` for each merge
// commit the push `pushed` sends from the repo `dir`, given as git gives pre-push its stdin, a
// `<local ref> <local sha> <remote ref> <remote sha>` line per ref. A ref new to the remote, or
// whose remote commit isn't here, is checked against every remote-tracking branch. Any other is
// checked against its remote commit and each remote's default branch, which has the merges a
// branch rebased onto it brings along; that remote's tracking ref of the branch pushed to doesn't
// count, as the push replaces it. A deletion sends no commits. It errs where git does, such as on
// a commit not in the repo.
func LinearHistory(dir, pushed string) ([]string, error) {
	defaults, err := git(dir, "for-each-ref", "--format=%(refname) %(symref)", "refs/remotes/*/HEAD")
	if err != nil {
		return nil, err
	}
	var found []string
	for _, line := range strings.Split(pushed, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 4 || strings.Trim(fields[1], "0") == "" {
			continue
		}
		ref, local, to, remote := fields[0], fields[1], fields[2], fields[3]
		sends := []string{local, "--not", "--remotes"}
		if strings.Trim(remote, "0") != "" {
			if _, err := git(dir, "cat-file", "-e", remote+"^{commit}"); err == nil {
				sends = []string{local, "--not", remote}
				for _, line := range strings.Split(strings.TrimSpace(defaults), "\n") {
					head, branch, _ := strings.Cut(line, " ")
					if branch != "" && branch != strings.TrimSuffix(head, "HEAD")+strings.TrimPrefix(to, "refs/heads/") {
						sends = append(sends, branch)
					}
				}
			}
		}
		merges, err := git(dir, append([]string{"rev-list", "--merges"}, sends...)...)
		if err != nil {
			return nil, err
		}
		for _, commit := range strings.Fields(merges) {
			found = append(found, ref+" "+commit[:12])
		}
	}
	return found, nil
}
