import { defineConfig } from "astro/config";

import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://waal42.github.io",
  base: "/svatba",

  vite: {
    plugins: [tailwindcss()],
  },
});
