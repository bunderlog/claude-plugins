// eslint for the app: typescript-eslint's type-checked rules, Vue's recommended ones and
// vue-modular's layout and names, with layout of the code left to prettier (ADR stack). In
// TypeScript, so that eslint loads it through jiti, which vue-modular's build needs (ADR stack).
import { defineConfig } from "eslint/config";
import prettier from "eslint-config-prettier";
import vue from "eslint-plugin-vue";
import vueModular from "eslint-plugin-vue-modular";
import tseslint from "typescript-eslint";

export default defineConfig(
  { ignores: ["dist"] },
  {
    files: ["**/*.{ts,vue}"],
    extends: [tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        projectService: true,
        extraFileExtensions: [".vue"],
      },
    },
  },
  // After typescript-eslint's, whose parser it replaces for .vue files with vue-eslint-parser,
  // which hands each script block to typescript-eslint's.
  vue.configs["flat/recommended"],
  vueModular.configs.recommended,
  // A page's test sits beside it in views/ (the vue Guideline).
  {
    rules: {
      "vue-modular/views-suffix": ["error", { ignores: ["**/*.test.ts"] }],
    },
  },
  prettier,
);
