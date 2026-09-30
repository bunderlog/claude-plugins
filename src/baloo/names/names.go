// Package names holds every name the plugin is known by, so a rename is one edit here.
package names

const (
	// Plugin is the plugin's name, its binary's name and the prefix of the binary's file names.
	Plugin = "baloo"
	// PluginDir is the plugin's folder in this repo.
	PluginDir = "plugins/" + Plugin
	// Src is the binary's Go module, beside the plugin rather than in it (ADR plugin).
	Src = "src/" + Plugin
	// Manifest is the plugin's manifest; its version is the plugin's and the binary's.
	Manifest = PluginDir + "/.claude-plugin/plugin.json"
)

// Binary is the file name of the binary of `version` for one platform, as the Loader looks for it.
func Binary(version, goos, goarch string) string {
	return Plugin + "_" + version + "_" + goos + "_" + goarch
}
