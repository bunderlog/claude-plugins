// HomeView, the app's home page, shows the product's name (ADR stack).
import { mount } from "@vue/test-utils";
import { expect, test } from "vitest";
import HomeView from "./HomeView.vue";

test("shows the product name", () => {
  expect(mount(HomeView).text()).toContain("__NAME__");
});
