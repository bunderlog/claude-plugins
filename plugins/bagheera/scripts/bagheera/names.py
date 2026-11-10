"""Every name the plugin is known by, so a rename is one edit here (ADR plugin)."""

# The plugin's name.
PLUGIN = "bagheera"
# The marketplace the plugin is in, this repo.
MARKETPLACE = "bunderlog"
# The plugin as Claude Code's settings name it, in enabledPlugins.
PLUGIN_ID = PLUGIN + "@" + MARKETPLACE
# The plugin whose skills a Session review loads, glossary and adr, and whose files it reads only:
# the project's method, beside this plugin in the marketplace (PRD bagheera).
KNOWLEDGE = "baloo"
# The plugin's folder in this repo.
PLUGIN_DIR = "plugins/" + PLUGIN
# The plugin's manifest; its version is the plugin's.
MANIFEST = PLUGIN_DIR + "/.claude-plugin/plugin.json"
# The Config an earlier baloo read, from a repo's root, which doctor names for removal.
OLD_CONFIG = ".claude/baloo.yml"
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
# Marks what the plugin wrote into a file it shares, so it knows it for its own: the statusLine
# command a person sets from it.
MARKER = "# managed by " + PLUGIN
# What an earlier baloo marked the statusLine it wrote into a clone's local settings with.
OLD_MARKER = "# managed by baloo"
