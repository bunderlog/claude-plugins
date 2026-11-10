// The app's entry: mounts App with its router and the theme (ADR stack).
import { createApp } from "vue";
import App from "./App.vue";
import "./main.css";
import { router } from "./router";

createApp(App).use(router).mount("#app");
