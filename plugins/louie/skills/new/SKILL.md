---
name: new
description: Start a new Go and Vue product from louie's go-vue template — when the user asks to start, create or scaffold a new product, app or project of this stack in a new or empty folder outside any git repo. Asks the product's name and its GitHub owner, writes the template there with git init on main, and gives the one line that turns the Git hooks on and makes the first commit. Not for an existing project, which is set up instead (PRD project-setup), or another stack.
argument-hint: <path>
---

# New

You are starting a product someone will build on for years: write nothing they didn't agree to,
and leave the first commit to them.

1. Take the folder from the arguments, `$ARGUMENTS`; without one, ask for it. It must be a new
   folder, or an empty one, outside any git repo.
2. Ask the product's name: lowercase letters, digits and hyphens, starting with a letter, since it
   serves as the Go module's, the npm package's and Kamal's name.
3. Ask the GitHub owner, user or organization, the repo will be under. Offer the `gh` user as the
   default, from `gh api user --jq .login`; where `gh` is missing or logged out, ask with no
   default.
4. Run, with each value in single quotes:

   ```sh
   python3 -E -s '${CLAUDE_PLUGIN_ROOT}/scripts/run.py' new '<path>' '<name>' '<owner>'
   ```

5. On exit 1, tell the person the reason it printed after `louie:`; nothing was written, so they
   can pick another folder or name and you run it again. On exit 2, it couldn't run: tell them
   what it printed.
6. On exit 0, give the person its last line as it is, starting with `!`, for them to run
   themselves: it turns the Git hooks on and makes the first commit, which then carries no trailer
   of yours. Don't run it, and don't commit for them.
7. Then name what comes next, theirs to run, without running it: creating the GitHub repo and
   pushing, such as `gh repo create <owner>/<name> --private --source . --push` in the new
   folder; running it with `mise run dev`; and deploying, as the new repo's README says: filling
   in `config/deploy.yml`'s `<server>` and `<registry>` and the secrets of `.env`, copied from
   `.env.example`, then `mise run deploy setup`.
