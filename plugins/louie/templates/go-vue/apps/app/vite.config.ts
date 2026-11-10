// Vite's build and Vitest's tests of the app: Vue, Tailwind 4 and the `@/` alias to src, in jsdom
// (ADR stack).
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },
  test: { environment: "jsdom" },
});
