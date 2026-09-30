package checks

import "strings"

// LinearHistory is the Check baloo:linear-history (pre-push): `<ref> <commit>` for each merge
// commit the push `pushed` sends from the repo `dir`, given as git gives pre-push its stdin, a
// `<local ref> <local sha> <remote ref> <remote sha>` line per ref. A ref new to the remote, or
// whose remote commit isn't here, is checked against every remote-tracking branch; a deletion
// sends no commits. It errs where git does, such as on a commit not in the repo.
func LinearHistory(dir, pushed string) ([]string, error) {
	var found []string
	for _, line := range strings.Split(pushed, "\n") {
		fields := strings.Fields(line)
		if len(fields) < 4 || strings.Trim(fields[1], "0") == "" {
			continue
		}
		ref, local, remote := fields[0], fields[1], fields[3]
		sends := []string{local, "--not", "--remotes"}
		if strings.Trim(remote, "0") != "" {
			if _, err := git(dir, "cat-file", "-e", remote+"^{commit}"); err == nil {
				sends = []string{remote + ".." + local}
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
