// tailwind.config.mjs
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}"],
  theme: {
    extend: {
      colors: {
        wedding: {
          black: "#000000",
          white: "#ffffff",
          gray: "#aaaaaa",
        },
      },
      fontFamily: {
        sans: ["Capsuula", "sans-serif"],
      },
    },
  },
  plugins: [],
};
