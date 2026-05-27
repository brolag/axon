# axon docs site

The documentation site for [axon](../README.md), built with [Astro](https://astro.build)
(static output, no client framework). Brand: Indie Mind.

## Local development

```bash
cd site
npm install
npm run dev      # http://localhost:4321/axon
```

## Build

```bash
npm run build    # static output in site/dist
npm run preview  # serve the built output locally
```

The build runs with zero runtime JavaScript except a small clipboard handler for the
code-block copy buttons.

## Deploy to GitHub Pages

### Automated (recommended)

A workflow at [`.github/workflows/deploy-site.yml`](../.github/workflows/deploy-site.yml)
builds `site/` and deploys to GitHub Pages on every push to `main` that touches `site/`.

One-time setup in the repository:

1. Settings -> Pages -> Build and deployment -> Source: **GitHub Actions**.
2. Push to `main`. The workflow builds and publishes automatically.

The site will be served at `https://<user>.github.io/axon/`.

### Manual

```bash
cd site
npm install
npm run build
npx gh-pages -d dist        # publishes site/dist to the gh-pages branch
```

If you use the manual `gh-pages` branch flow, set Settings -> Pages -> Source to
**Deploy from a branch** -> `gh-pages` -> `/ (root)`.

## Base path

`astro.config.mjs` sets `site` and `base: '/axon'` so links and assets resolve under the
project-pages path `https://<user>.github.io/axon/`. All internal links go through the
`withBase()` helper in `src/lib/paths.ts`, so changing the base in one place is enough.

For a user/org root site or a custom domain, set `base: '/'` and update `site`.

## Hero image

The landing hero reserves a band for `public/assets/hero.png`. If the file is absent the
page falls back to a CSS watercolor gradient, so the build is valid either way. See
`public/assets/README.md`.

## Structure

```
site/
  astro.config.mjs        site + base for GitHub Pages
  src/
    layouts/              Base (shell, fonts, header/footer) + DocsLayout (sidebar)
    components/           Header, Footer, AxonLine (neural motif), CodeBlock (copy button)
    lib/paths.ts          withBase() for base-path-safe links
    pages/
      index.astro         landing: hero, pitch, comparison, install, quickstart
      docs/
        architecture.astro
        safety.astro
        evaluation.astro
        cli.astro
        contributing.astro
    styles/global.css     Indie Mind brand system (colors, type, components)
  public/assets/          hero.png goes here
```
