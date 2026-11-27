# louie reaches the Code host through an MCP server of its own

Date: 2026-11-27

Every stage of `/louie:implement` and `/louie:merge` that asks the Code host something (the repo,
a pull request, its checks, a merge) calls the tools of louie's MCP server `code-host`, on GitHub
and on Bitbucket Cloud alike (PRD code-host). The server tells the Code host from the remote
`origin`, calls `gh` on GitHub and Bitbucket's API on Bitbucket Cloud, and holds in its code the
rules a merge rests on, which were text in the implementer's instructions (ADR merge). Its tools'
names stay the same from Release to Release, so a person allows them once in their settings and
the implementer's `tools:` names them, where a command's path in the plugin cache changes with
each Release; and each tool takes typed parameters, so no agent builds a command line.

The server is the plugin's own Python, standard library only, Python 3.9 and later, as the Hooks'
code is (ADR binary): `scripts/run.py mcp` speaks MCP over stdio, declared in the plugin's
manifest with `${CLAUDE_PLUGIN_ROOT}`. Its logic is functions the tests call directly; the
protocol is a thin layer over them, tested once on its own.

## Considered options

- A `code-host` command run through `run.py`, as the skills run `doctor` — no process for the
  session's length, but its path changes with each Release, so the Workflow had to hand it to
  every stage, a person had no stable rule to allow it, and the agent wrote each call as a string.
- The Code hosts' own MCP servers, GitHub's and Atlassian's — nothing to write, but two interfaces
  for one stage, the merge's rules still text, and each taking its token its own way.

## Consequences

- In a project with louie on, every session starts the server, one more Python process, whether a
  Workflow runs or not; its tools are visible outside a Workflow too, where they keep the same
  rules.
- Without `python3`, or when the server fails to start, the tools are missing and the stages that
  need them stop; Claude Code shows the server's failure.
- The server reads the environment once, when the session starts: a token set later needs a
  restart.
- The tools' names and parameters are what people's allow rules and the implementer name: renaming
  one is a breaking change, made in a Release that says so.
- Revisit when Workflow stages can't reach a plugin's MCP tools, or the server's start shows in a
  session's start time.
