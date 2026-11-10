# The `go-vue` template gets `apps/app`, a Vue app in a pnpm workspace

2026-11-10

## Symptom

The third of PRD templates' four Issues: `/louie:new` writes a project with `apps/api` (0.47.0)
and no front end. This one adds `apps/app`, the Vue 3 app in TypeScript with Tailwind, Vitest and
eslint, joined by a pnpm workspace, and its part of `mise run check`. Then comes the last Issue:
`mise run dev`, the database wiring, the Dockerfile, Kamal's `config/deploy.yml` and the CI job
running `mise run dev`.

## Evidence

- PRD templates, Scope: `apps/app`, a Vue 3 app in TypeScript with Tailwind, Vitest and eslint,
  named for the address it serves; a pnpm workspace, its `pnpm-lock.yaml` committed with no
  product name in it; Node and pnpm pinned in `mise.toml`; louie's Guidelines win over the
  projects it is cut from (eslint with their rules).
- `~/Projects/chainofsale/apps/app/package.json` and its `pnpm-workspace.yaml`: the packages and
  versions; its ADR stack: pnpm over bun, Node on its LTS line, no Turbo.
- `plugins/louie/guidelines/vue.md`, `typescript.md` and `tailwind.md`: the layout, names, tests
  and Tailwind configuration the app must follow.

## Acceptance criteria

- A repo fresh from `/louie:new` has `apps/app` in a pnpm workspace, with `pnpm-lock.yaml`
  committed; the lockfile holds no product name, and no file holds the template's marks.
- In it, `mise run check` installs from the frozen lockfile, then for `apps/app` runs eslint,
  prettier's check, `vue-tsc`, Vitest and `vite build`, and fails when any of them fails; it needs
  no database and no running API. A Vitest test mounts the app's home page and finds the product's
  name in it.
- Node and pnpm are pinned to exact versions in the template's `mise.toml`, and every package in
  `package.json` to an exact version.
- The template's `apps/app` follows louie's `vue`, `typescript` and `tailwind` Guidelines, and the
  template's ADR stack says why Vue, pnpm and Tailwind.
- In this repo, session start still names no stack Guideline that the template's files alone
  would call for; this repo's CI job that makes a repo from the template still commits it through
  its hooks and passes its `mise run check`.

## Comments

### 2026-11-10 · decision

Settled before planning, so the plan needn't ask:

- Versions are chainofsale's (Node 24.22.1 on the LTS line, pnpm 11.28.8, Vue 3.5.44, vue-router
  4.6.4, Vite 8.3.5, Vitest 4.1.12, Tailwind 4.3.3 through `@tailwindcss/vite`, TypeScript 5.9.3,
  vue-tsc 3.3.13), plus `@vue/test-utils`, eslint with `eslint-plugin-vue`, `typescript-eslint`
  and `eslint-plugin-vue-modular`'s recommended config, and prettier with
  `prettier-plugin-tailwindcss`, each at its latest release at least two weeks old, pinned exactly.
- The app's package is `@__NAME__/app`; `package.json` and `pnpm-workspace.yaml` carry `.tmpl`,
  as Issue louie-new-scaffold's decision listed, while `.vue` and `.ts` files keep their names.
- The layout is the `vue` Guideline's for a new app: `src/app/` (entry, router), `src/shared/`
  and `src/views/HomeView.vue`, a routed page that shows the product's name; no feature folder
  yet, since the template has no feature.
- No TanStack Query, Pinia, `cn()` or `cva` yet: the page fetches nothing, holds no shared state
  and takes no `class`, and the `typescript` Guideline asks for few dependencies; a product adds
  each when its first need comes. Calling `/api/up` from the app, and Vite's proxy to the API,
  come with `mise run dev`.
- The theme is Tailwind 4's `@theme` in the app's CSS, with dark mode through its tokens, and no
  `tailwind.config.js`.
