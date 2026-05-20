import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  site: 'https://waal42.github.io',
  base: '/dot-dot-both-dot',
  integrations: [tailwind()],
});
