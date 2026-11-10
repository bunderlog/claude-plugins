// What a `.vue` import is to TypeScript outside vue-tsc, such as typescript-eslint's type-checked
// rules (ADR stack).
declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
