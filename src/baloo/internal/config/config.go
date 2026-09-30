// Package config reads a repo's Config, .claude/baloo.yml, and writes a new one (ADR config). A
// Config that is wrong in part still applies in part: each wrong setting is a problem, one line
// for Claude, and its default applies, so a mistake never stops a Check.
package config

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"go.yaml.in/yaml/v3"

	"github.com/bunderlog/claude-plugins/src/baloo/names"
)

// Config is a repo's settings. Each Check adds its field here, its key to keys and to the schema,
// and its key, turned on, to template.
type Config struct {
	// Root is the root of the repo whose Config this is, or "" where the repo has none (see
	// Load).
	Root string
	// OutputStyle is the plugin's Output style that session start picks where Claude Code's
	// settings pick none (ADR output-styles), or "" for none.
	OutputStyle string
}

// OutputStyles are the plugin's Output styles, the files in its output-styles/.
var OutputStyles = []string{"short-replies"}

// keys decodes each setting's value into a Config; a key that isn't here is not a setting.
var keys = map[string]func(c *Config, value *yaml.Node) error{
	"output-style": func(c *Config, value *yaml.Node) error {
		var off bool
		if value.Tag == "!!bool" && value.Decode(&off) == nil && !off {
			c.OutputStyle = ""
			return nil
		}
		if value.Tag != "!!str" || !slices.Contains(OutputStyles, value.Value) {
			return fmt.Errorf("is not false or one of %s", strings.Join(OutputStyles, ", "))
		}
		c.OutputStyle = value.Value
		return nil
	},
}

// template is a new Config: it names the schema for editors, and says in plain words how the
// settings work, for someone who has read neither the schema nor the README.
const template = "# yaml-language-server: $schema=" + names.Schema + `
#
# baloo's settings for this repo. Each check turns on with a key of its own here, and without it
# is off. A wrong setting is reported at session start, and its default applies.

# The Output style for Claude's replies, picked at session start in the settings file that
# enables the plugin, where no settings file of Claude Code's picks one; false picks none.
output-style: short-replies
`

// repo is the root of the repo `dir` is in, where its Config is: the nearest folder up from `dir`
// that holds a .git, or `dir` itself outside a repo, with whether `dir` is in a repo at all.
func repo(dir string) (string, bool) {
	for d := dir; ; {
		if _, err := os.Stat(filepath.Join(d, ".git")); err == nil {
			return d, true
		}
		parent := filepath.Dir(d)
		if parent == d {
			return dir, false
		}
		d = parent
	}
}

// Load reads the Config of the repo `dir` is in, with its problems, after creating it when the
// repo has none (see create); it also returns the path of one it created. Outside a repo, when the
// repo is the home folder itself (a dotfiles repo), or when it is in Claude Code's own folder, it
// neither reads nor writes one, and every setting has its default: the home folder's .claude/ is
// Claude Code's own settings, not a repo's, and what is inside it is Claude Code's to write.
func Load(dir string) (c Config, created string, problems []string) {
	root, inRepo := repo(dir)
	if !inRepo || claudeCodes(root) {
		return c, "", nil
	}
	created, err := create(root)
	var pathErr *fs.PathError
	switch {
	case errors.As(err, &pathErr): // it names the path already
		problems = append(problems, fmt.Sprintf("could not create %s: %v", pathErr.Path, pathErr.Err))
	case err != nil:
		problems = append(problems, fmt.Sprintf("could not create %s: %v", names.Config, err))
	}
	c, more := read(root)
	c.Root = root
	return c, created, append(problems, more...)
}

func read(root string) (Config, []string) {
	data, err := os.ReadFile(filepath.Join(root, names.Config))
	if errors.Is(err, fs.ErrNotExist) {
		return Config{}, nil
	}
	if err != nil {
		return Config{}, []string{fmt.Sprintf("%s: %v; none of it applies", names.Config, err)}
	}
	return parse(data)
}

func parse(data []byte) (Config, []string) {
	var c Config
	var doc yaml.Node
	if err := yaml.Unmarshal(data, &doc); err != nil {
		why := strings.TrimPrefix(err.Error(), "yaml: ")
		return c, []string{fmt.Sprintf("%s: %s; none of it applies", names.Config, why)}
	}
	if len(doc.Content) == 0 { // empty, or only comments
		return c, nil
	}
	top := doc.Content[0]
	if top.Kind != yaml.MappingNode {
		return c, []string{fmt.Sprintf("%s line %d: not a map of settings; none of it applies",
			names.Config, top.Line)}
	}
	var problems []string
	for i := 0; i+1 < len(top.Content); i += 2 {
		key, value := top.Content[i], top.Content[i+1]
		set, ok := keys[key.Value]
		if !ok {
			problems = append(problems, fmt.Sprintf("%s line %d: %s is not a setting; ignored",
				names.Config, key.Line, key.Value))
			continue
		}
		if err := set(&c, value); err != nil {
			problems = append(problems, fmt.Sprintf("%s line %d: %s: %v; its default applies",
				names.Config, key.Line, key.Value, err))
		}
	}
	return c, problems
}

// create writes a new Config, every Check on, at the repo root `root` when it has none, and returns
// its path; with a Config there already, it writes nothing and returns "".
func create(root string) (string, error) {
	path := filepath.Join(root, names.Config)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return "", err
	}
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
	if errors.Is(err, fs.ErrExist) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	_, err = f.WriteString(template)
	if cerr := f.Close(); err == nil {
		err = cerr
	}
	if err != nil {
		// Half a Config would pass for the user's own from then on, and never be written again.
		os.Remove(path)
		return "", err
	}
	return path, nil
}

// claudeCodes says whether the repo root `root` is the home folder, or Claude Code's own folder,
// CLAUDE_CONFIG_DIR or ~/.claude, or inside it, such as a marketplace it cloned.
func claudeCodes(root string) bool {
	home, err := os.UserHomeDir()
	if err == nil && resolve(root) == resolve(home) {
		return true
	}
	own := os.Getenv("CLAUDE_CONFIG_DIR")
	if own == "" {
		if err != nil {
			return false
		}
		own = filepath.Join(home, ".claude")
	}
	rel, err := filepath.Rel(resolve(own), resolve(root))
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

// resolve is the path `p` with its links followed, so two spellings of one folder compare equal.
func resolve(p string) string {
	if r, err := filepath.EvalSymlinks(p); err == nil {
		return r
	}
	return filepath.Clean(p)
}
