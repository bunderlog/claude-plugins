// The app's routes, each with a name to navigate by; a path is written only here. Each page is
// loaded when its route is first visited (ADR stack).
import { createRouter, createWebHistory } from "vue-router";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
  ],
});
