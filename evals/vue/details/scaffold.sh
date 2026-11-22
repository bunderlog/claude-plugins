#!/bin/bash
# A Vue 3.5 app laid out by feature, with the monitors feature's list route and its API calls but
# no data layer around them yet: where a page fetches, how it navigates and how its component
# declares props are the page's to choose.
set -euo pipefail
git init -q -b main
mkdir -p src/app src/features/monitors/views src/features/monitors/services src/shared
cat > package.json <<'R'
{
  "name": "monitor-web",
  "private": true,
  "type": "module",
  "scripts": { "dev": "vite", "build": "vue-tsc -b && vite build", "test": "vitest run" },
  "dependencies": {
    "@tanstack/vue-query": "^5.90.0",
    "pinia": "^3.0.0",
    "vue": "^3.5.0",
    "vue-router": "^4.6.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.1.0",
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.4.0",
    "jsdom": "^27.0.0",
    "tailwindcss": "^4.1.0",
    "typescript": "^5.9.0",
    "vite": "^7.0.0",
    "vitest": "^4.0.0",
    "vue-tsc": "^3.0.0"
  }
}
R
cat > src/app/main.ts <<'R'
// The app's entry: Vue with its router, Pinia and TanStack Query.
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import { router } from './router'
import './main.css'

createApp(App).use(router).use(createPinia()).use(VueQueryPlugin).mount('#app')
R
cat > src/app/App.vue <<'R'
<script setup lang="ts"></script>

<template>
  <RouterView />
</template>
R
cat > src/app/main.css <<'R'
@import "tailwindcss";

@theme {
  --color-surface: #ffffff;
  --color-on-surface: #1f2937;
  --color-success: #15803d;
  --color-on-success: #ffffff;
  --color-error: #b91c1c;
  --color-on-error: #ffffff;
}
R
cat > src/app/router.ts <<'R'
// The app's router: each feature's routes.
import { createRouter, createWebHistory } from 'vue-router'
import { routes as monitors } from '@/features/monitors'

export const router = createRouter({ history: createWebHistory(), routes: [...monitors] })
R
cat > src/features/monitors/index.ts <<'R'
// The monitors feature's public API.
export { routes } from './routes'
export type { Monitor, MonitorStatus } from './services/monitors'
R
cat > src/features/monitors/routes.ts <<'R'
import type { RouteRecordRaw } from 'vue-router'

export const routes: RouteRecordRaw[] = [
  { path: '/monitors', name: 'monitors', component: () => import('./views/MonitorsView.vue') },
]
R
cat > src/features/monitors/views/MonitorsView.vue <<'R'
<script setup lang="ts"></script>

<template>
  <h1 class="text-on-surface text-xl">Monitors</h1>
</template>
R
cat > src/features/monitors/services/monitors.ts <<'R'
// The monitors API: one function per request.

export type MonitorStatus = 'up' | 'down' | 'paused'

export type Monitor = { id: string; url: string; status: MonitorStatus }

export async function getMonitor(id: string): Promise<Monitor> {
  const response = await fetch(`/api/monitors/${encodeURIComponent(id)}`)
  if (!response.ok) throw new Error(`monitor ${id}: ${response.status}`)
  return (await response.json()) as Monitor
}

export async function pauseMonitor(id: string): Promise<void> {
  const response = await fetch(`/api/monitors/${encodeURIComponent(id)}/pause`, { method: 'POST' })
  if (!response.ok) throw new Error(`pause ${id}: ${response.status}`)
}
R
cat > tsconfig.json <<'R'
{
  "compilerOptions": {
    "target": "es2022",
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "noEmit": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
R
git add -A
git -c user.name=dev -c user.email=dev@example.com commit -q -m "Start the monitor web app"
