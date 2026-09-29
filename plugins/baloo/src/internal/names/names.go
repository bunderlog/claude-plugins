// Package names holds every name the plugin is known by, so a rename is one edit here.
package names

const (
	// Plugin is the plugin's name, its binary's name and the prefix of its builds.
	Plugin = "baloo"
	// Repo is the GitHub repo whose Releases hold the builds.
	Repo = "bunderlog/claude-plugins"
	// PluginDir is the plugin's folder in this repo.
	PluginDir = "plugins/" + Plugin
	// Src is the binary's Go module, inside the plugin it belongs to.
	Src = PluginDir + "/src"
	// Manifest is the plugin's manifest; its version is the plugin's and the binary's.
	Manifest = PluginDir + "/.claude-plugin/plugin.json"
	// Sums lists the sha256 of each build of the current version, beside the loader that checks them.
	Sums = PluginDir + "/scripts/SHA256SUMS"
)

// Build is the file name of the build of `version` for one platform, as the loader looks for it.
func Build(version, goos, goarch string) string {
	return Plugin + "_" + version + "_" + goos + "_" + goarch
}
