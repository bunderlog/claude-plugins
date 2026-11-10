"""Every name the plugin is known by, so a rename is one edit here (ADR plugin)."""

# The plugin's name.
PLUGIN = "louie"
# The marketplace the plugin is in, this repo.
MARKETPLACE = "bunderlog"
# The plugin as Claude Code's settings name it, in enabledPlugins.
PLUGIN_ID = PLUGIN + "@" + MARKETPLACE
# The plugin's agent that the verify Workflow runs, as Claude Code names it.
VERIFIER = PLUGIN + ":verifier"
# The plugin's folder in this repo.
PLUGIN_DIR = "plugins/" + PLUGIN
# Claude Code's own settings files of a project, from its folder: the team's and one person's.
PROJECT_SETTINGS = ".claude/settings.json"
LOCAL_SETTINGS = ".claude/settings.local.json"
