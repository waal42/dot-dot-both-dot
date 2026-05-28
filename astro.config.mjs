import { defineConfig } from "astro/config";

import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://mywalove.cz",
  base: "/svatba",

  vite: {
    plugins: [tailwindcss()],
  },
});
