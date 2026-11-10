// Vite's build and Vitest's tests of the app: Vue, Tailwind 4 and the `@/` alias to src, in jsdom.
// In dev, /api goes to the API that `mise run dev` runs on :8080; in production the Go binary
// serves the build and the API on one port (ADR stack).
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },
  server: { proxy: { "/api": "http://localhost:8080" } },
  test: { environment: "jsdom" },
});
