# louie gives Claude a Docker Guideline when it works on a Dockerfile or a Compose file

## Problem

Claude writing a Dockerfile or a Compose file in a project with louie on gets no rules for it,
where Go, Python, TypeScript and Vue code gets its Guideline from a Hook (ADR guidelines). The
mistakes a bare model makes there don't fail the build, so nobody sees them: of this machine's
Docker files on 2026-11-22, 6 of 17 Dockerfiles run as root, 6 build from a folder with no
`.dockerignore`, so `COPY . .` copies an Env file into the image (a Leak), and 5 of 9 Compose
files carry the obsolete `version:` key.

## Users

- Everyone in a project with louie on who has Claude write or change a Dockerfile or a Compose
  file.
- Not for: a project that wants its own container rules instead; its documented conventions win
  over the Guideline, as for every stack.

## Success signal

- Each rule in `docker.md` has an eval case that fails without louie (ADR evals); a rule no case
  fails without is not in the file.
- In the Assessment after its Release, `docker` is in context before the first Edit of an
  existing Docker file in most sessions with one, as the Guidelines a Hook gives were (15 of 22,
  ADR guidelines).

## Scope

- `plugins/louie/guidelines/docker.md`, in the shape of `go.md` and `python.md` (numbered
  sections, each ending in a **Test:** line), the project's documented conventions and its
  files' pattern winning. Its rules, each kept only once its case fails without louie:
  1. **Not as root.** The image's last stage runs as a user other than root: a `USER` naming
     neither `root` nor `0`, or a base image whose default user isn't root (distroless
     `:nonroot`).
  2. **The build context without Secrets.** A `.dockerignore` at the build context's root, or a
     `<Dockerfile>.dockerignore` beside the Dockerfile, leaves out `.git` and every Env file; or
     the Dockerfile copies only named paths, never `.`.
  3. **Compose without `version:`.** A Compose file has no top-level `version:` key, which the
     Compose Specification made obsolete and `docker compose` warns about.
  4. **A Secret as a mount.** A Secret the build needs (a registry or package token) comes
     through `RUN --mount=type=secret`, never through `ARG` or `ENV`, which stay in the image's
     history or its environment.
- A Docker file is one named, at any depth in the repo: `Dockerfile` or `dockerfile`,
  `Containerfile`, `Dockerfile.<x>` or `<x>.Dockerfile` but one ending in `.dockerignore`, `.md`
  or `.txt`; `compose.yaml`, `compose.yml`, `compose.<x>.yaml`, `compose.<x>.yml`, and the same
  four starting `docker-compose`. louie's Hook and bagheera's Assessment match the same names
  (ADR plugin: each its own copy).
- louie's `PostToolUse` Hook gives it whole, once a session, on a Read, Edit, Write or MultiEdit
  of a Docker file in the repo, and logs it in `guidelines/guidelines.log`, as `python` on a
  `.py` file. Claude reads a repo's other Docker file before writing one, so a Dockerfile written
  where a Compose file exists, or the reverse, gets it first.
- Session start's index doesn't name it, as for `python`: the Hook gives it.
- The verifier is given it, its line "Writing a Dockerfile or a Compose file", as it is the other
  Guidelines that fit the repo, where the repo holds a Docker file outside the folders session
  start's walk skips.
- bagheera's Assessment counts `docker` before the first Edit or MultiEdit of a Docker file; a
  session whose first edit of one is the Write that creates it isn't counted either way.
- ADR guidelines names `docker` among the stacks, the Docker files among the Hook's signals, and
  the verifier's signal for it.

## Non-goals

- A repo's first Docker file written with the Guideline: the Hook gives it after the Write that
  creates the file, as for a new `.ts` file (ADR guidelines).
- A session start index line for `docker`.
- `.dockerignore` as a signal of its own: it is rarely edited alone, and rule 2 is about the
  build beside it.
- The verifier given `docker` for a Docker file only in a hidden folder or a skipped one
  (`.devcontainer/`, `build/`): session start's walk skips them, as for every stack.
- Lint rules a tool already checks (hadolint): `apt-get` without `--no-install-recommends`, a
  shell-form `CMD`, a base image without a tag.
- Other rules (multi-stage builds, layer order for the cache, a pinned digest, healthchecks,
  `depends_on` conditions): each comes only with a case that fails without louie.
- Kubernetes manifests, Helm charts, or a CI's image build.
- Fixing the projects' existing Docker files: the Guideline applies to what Claude writes.

## Anti-goals

- `docker` given where no Docker file is touched, or more than once in a session.
- A `USER` added unasked to an existing image that runs as root: its files' pattern wins, as it
  may bind a port below 1024 or write to a root-owned volume.

## Acceptance criteria

- A Read of a `Dockerfile` in the repo gives `docker.md` whole as added context, and the log has
  one line naming the session, `docker` and the file; a second Read or an Edit of a Docker file
  in the same session gives no `docker` again.
- A Read of each of `dockerfile`, `Dockerfile.www`, `api.Dockerfile`, `Containerfile`,
  `compose.yaml`, `compose.override.yml`, `docker-compose.yml` and `docker-compose.dev.yaml`
  gives it as a `Dockerfile` does; a Read of `.dockerignore`, `Dockerfile.dockerignore`,
  `Dockerfile.md`, `my-compose.yml` or `docker.md` gives no `docker`.
- A Read of a `Dockerfile` outside the repo gives no `docker`.
- Session start's index names no `docker` line, in a repo with a Docker file or without.
- The verifier's start gives a `docker` line in a repo with a `Dockerfile` or a `compose.yaml`,
  and none in a repo whose only one is under `node_modules/` or `dist/`.
- The Assessment counts a session that read a `Dockerfile`, was given `docker`, then edited it,
  as `docker` in context before the first Edit; one that edited a Compose file with no `docker`
  given first, as not; one whose only edit of a Docker file was the Write that created it, as
  neither.
- `docker.md` holds only rules whose case scored below 1.00 without louie on at least one of the
  default model and Claude Sonnet; a rule whose case scores 1.00 without it on both is dropped
  with its case.
- `evals/docker/user`: in a repo with a Node service and a `compose.yaml` that builds it from
  `.`, Claude, asked to write the service's `Dockerfile` at the root, makes its last stage run
  as a user other than root; it scores 1.00 with louie on both models, 3 runs an arm.
- `evals/docker/dockerignore`: in the same repo, holding a `.env` and no `.dockerignore`, Claude,
  asked the same, leaves `.env` and `.git` out of what the image copies: a `.dockerignore` at
  the root names both, or the `Dockerfile` copies no `.`; scored as above.
- `evals/docker/compose`: in a repo with a Node service and its `Dockerfile`, Claude, asked to add
  a `compose.yaml` running the service with a Postgres, writes no top-level `version:`; scored
  as above.
- `evals/docker/secret`: in a repo whose `.npmrc` reads a private registry's token from
  `NPM_TOKEN` and whose `compose.yaml` builds the service from `.`, Claude, asked to write the
  `Dockerfile` at the root, passes the token through `RUN --mount=type=secret`, with no `ARG` or
  `ENV` naming `NPM_TOKEN`; scored as above.
