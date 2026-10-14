"""Every name the plugin is known by, so a rename is one edit here (ADR plugin)."""

# The plugin's name.
PLUGIN = "baloo"
# The marketplace the plugin is in, this repo.
MARKETPLACE = "bunderlog"
# The plugin as Claude Code's settings name it, in enabledPlugins.
PLUGIN_ID = PLUGIN + "@" + MARKETPLACE
# The plugin's agent that the verify skill runs, as Claude Code names it.
VERIFIER = PLUGIN + ":verifier"
# The plugin's folder in this repo.
PLUGIN_DIR = "plugins/" + PLUGIN
# The plugin's manifest; its version is the plugin's.
MANIFEST = PLUGIN_DIR + "/.claude-plugin/plugin.json"
# A repo's Config file, from its root: beside Claude Code's own settings.
CONFIG = ".claude/" + PLUGIN + ".yml"
# Claude Code's own settings files of a project, from its folder: the team's and one person's.
PROJECT_SETTINGS = ".claude/settings.json"
LOCAL_SETTINGS = ".claude/settings.local.json"
# A repo's glossary, its folder of ADRs and its folder of PRDs, from its root.
GLOSSARY = ".about/glossary.md"
ADRS = ".about/adr/"
PRDS = ".about/prd/"
# A repo's folder of the Session reviews' Proposals, from its root.
PROPOSALS = ".about/proposals/"
# A repo's file of what is still to consider, one `## ` heading per item, from its root.
INBOX = ".about/inbox.md"
# The Config's key of the project's own commands the Git hooks run after their Checks;
# `GIT_HOOK_COMMANDS + "." + <hook>` names one.
GIT_HOOK_COMMANDS = "git-hook-commands"
# Marks what the plugin wrote into a file it shares, so it knows it for its own: the statusLine
# command, a Git hook, husky's line.
MARKER = "# managed by " + PLUGIN
# Where editors find the Config's JSON Schema, which a new Config names.
SCHEMA = (
    "https://raw.githubusercontent.com/bunderlog/claude-plugins/main/" + PLUGIN_DIR + "/schema.json"
)
