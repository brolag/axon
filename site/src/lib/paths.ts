// Join Astro's configured base with an internal path so links work both on
// GitHub Pages (served at /axon) and at the root. Avoids double slashes.
const BASE = import.meta.env.BASE_URL; // e.g. "/axon" or "/"

export function withBase(path: string): string {
  const base = BASE.replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${base}${p}` || '/';
}
