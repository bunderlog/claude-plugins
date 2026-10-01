# Vue

For writing Vue 3 with TypeScript: the choices where more than one would be reasonable.
`typescript.md` covers the TypeScript. These are defaults for a new app: in an existing one, its
documented conventions and the pattern its code already follows win, the layout, data layer and
tests' too.

## 1. Layout by feature

- A new app is feature-first: `src/app/` (entry, router, layouts), `src/shared/` (UI kit,
  cross-cutting composables, services, stores, types), `src/features/<feature>/` (its own
  components, composables, services, stores, views, `routes.ts`, and `index.ts` as its public
  API), and `src/views/` for pages no feature owns.
- A feature imports only from `shared/` and itself; `shared/` never imports a feature. Others
  reach a feature through its `index.ts`, never a deep path. Relative imports inside a feature,
  the `@/` alias across layers.
- `eslint-plugin-vue-modular` with its recommended config checks this layout and the names
  below; add it to a new app rather than keeping these rules by hand.
- Navigate by route name (`router.push({ name: 'monitor', params })`); a route's path is written
  only in its `routes.ts`.

**Test:** removing a feature's folder breaks only the imports of its `index.ts`.

## 2. Names

- Components PascalCase `.vue`; a routed page ends in `View.vue`. TypeScript files camelCase,
  folders kebab-case.
- A composable is `useX.ts`. A store or service is named for its domain, without a suffix:
  `auth.ts`, not `authStore.ts` or `authService.ts`; the store it defines is `useAuthStore`.

**Test:** a file's name says what it holds without opening it.

## 3. Components

- `<script setup lang="ts">`, then `<template>`, then `<style>` if there is one; no Options API.
- Props, emits and models are typed where they're declared: `defineProps<{ monitor: Monitor }>()`,
  `defineEmits<{ saved: [id: string] }>()`, `defineModel<string>()`.
- Styling comes from Tailwind classes and the design system's tokens (`tailwind.md`); a `<style>`
  block is the exception.
- A component renders and reacts. Fetching and business rules live in a composable it calls.

**Test:** a component's script is mostly wiring: props, a composable, handlers.

## 4. State

- Server data lives in TanStack Query, behind one composable per resource (`useMonitors()`)
  that calls a service (`api/monitors.ts`) for the requests: a plain module with one function
  per request, not a class in a DI container.
- Pinia holds only client state that outlives a component, such as the signed-in user, as a
  setup store: `defineStore('auth', () => { … })`. It is the one home for shared state: no
  module-level `ref` or `createGlobalState` beside it.
- A store used by more than one feature is a shared interface: add to it freely; rename or
  remove a member only together with every caller.
- Pass a ref, a computed or a getter to anything that outlives setup (a composable, a watcher, a
  store), never its `.value`: a `.value` read in setup is a snapshot that never updates. Derive
  with `computed`, or `watch` the source; don't copy reactive state into another ref.
- After a write, invalidate or refetch what it changed, and write from the loaded record, not
  from a list row's partial copy of it.

**Test:** no store keeps a copy of data the server owns, no module outside a store holds state at
its top level, and every view shows the server's data after a write.

## 5. Tests

- Vitest with `@vue/test-utils`: mount a component with its props, then check what it renders
  and emits.
- Each test gets a fresh Pinia: `setActivePinia(createPinia())` in `beforeEach`.
- A test that starts timers uses fake ones and restores real timers in `afterEach`: an interval
  left running fires into the next test.
- After mounting, or calling a composable that fetches as it starts, `await flushPromises()`
  before checking.
- `vi.hoisted()` runs before the file's imports, so it can't use them; import inside it:
  `const count = await vi.hoisted(async () => (await import('vue')).ref(0))`.

**Test:** each test passes alone and in any order.
