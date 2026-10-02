// Package names holds every name the plugin is known by, so a rename is one edit here.
package names

const (
	// Plugin is the plugin's name, its binary's name and the prefix of the binary's file names.
	Plugin = "baloo"
	// Marketplace is the marketplace the plugin is in, this repo.
	Marketplace = "bunderlog"
	// PluginID is the plugin as Claude Code's settings name it, in enabledPlugins.
	PluginID = Plugin + "@" + Marketplace
	// Verifier is the plugin's agent that the verify skill runs, as Claude Code names it.
	Verifier = Plugin + ":verifier"
	// PluginDir is the plugin's folder in this repo.
	PluginDir = "plugins/" + Plugin
	// Src is the binary's Go module, beside the plugin rather than in it (ADR plugin).
	Src = "src/" + Plugin
	// Manifest is the plugin's manifest; its version is the plugin's and the binary's.
	Manifest = PluginDir + "/.claude-plugin/plugin.json"
	// Config is a repo's Config file, from its root: beside Claude Code's own settings.
	Config = ".claude/" + Plugin + ".yml"
	// ProjectSettings and LocalSettings are Claude Code's own settings files of a project, from
	// its folder: the team's and one person's.
	ProjectSettings = ".claude/settings.json"
	LocalSettings   = ".claude/settings.local.json"
	// ADRs is a repo's folder of ADRs, from its root.
	ADRs = ".about/adr/"
	// Inbox is a repo's file of what is still to consider, one `## ` heading per item, from its
	// root.
	Inbox = ".about/inbox.md"
	// Marker marks what the plugin wrote into a file it shares, so it knows it for its own: the
	// statusLine command, a Git hook, husky's line.
	Marker = "# managed by " + Plugin
	// Schema is where editors find the Config's JSON Schema, which a new Config names.
	Schema = "https://raw.githubusercontent.com/bunderlog/claude-plugins/main/" + PluginDir +
		"/schema.json"
)

// Binary is the file name of the binary of `version` for one platform, as the Loader looks for it.
func Binary(version, goos, goarch string) string {
	return Plugin + "_" + version + "_" + goos + "_" + goarch
}
