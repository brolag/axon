// @ts-check
import { defineConfig } from 'astro/config';

// GitHub Pages deploy config.
// If the repo is served at https://<user>.github.io/axon/ keep base: '/axon'.
// For a user/org root site or a custom domain, set base: '/'.
export default defineConfig({
  site: 'https://brolag.github.io',
  base: '/axon',
  trailingSlash: 'ignore',
  build: {
    inlineStylesheets: 'auto',
  },
});
