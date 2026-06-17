## Context

The frontend is a Vite static site on Render at a custom domain. Social unfurls are driven entirely by static `<head>` tags + a reachable image; analytics is a single third-party script. Two constraints shaped the work: (1) the social card image must be a raster PNG at 1200×630 (most platforms don't render SVG for `og:image`), authored reproducibly rather than hand-drawn; (2) analytics must never run in local dev or in builds that haven't been configured.

## Goals / Non-Goals

- **Goals:** correct, complete unfurl metadata; an on-brand card + favicon generated reproducibly; privacy-first, opt-in analytics that is inert by default.
- **Non-goals:** dynamic/per-page OG images, server-side rendering for crawlers (static tags suffice for a single-page marketing surface), event/funnel analytics or session replay, and a cookie-consent flow (not needed for cookieless Umami).

## Decisions

### Static OG/Twitter tags in index.html
The app is effectively one shareable page, so static `<head>` metadata is sufficient — no SSR or prerender needed. `og:image`/`twitter:image` use **absolute** URLs (`https://worldcup.stagehopper.app/og-image.png`) because crawlers don't resolve relative paths. Image dimensions and `alt` are included so platforms can lay the card out without first fetching it.

### Generate the card; don't hand-author it
`scripts/make_social_assets.py` computes the soccer-ball geometry (a central pentagon + five rim pentagons clipped to a circle, with seams) and composes the 1200×630 card (dark gradient, ball, title, accent subtitle, tagline, URL), then rasterizes with `rsvg-convert`. Authoring as code makes the card editable and regenerable, and keeps the favicon and card visually consistent (same ball). The intermediate `og-image.svg` is rendered and removed; only the PNG ships.

### SVG favicon + PNG apple-touch-icon
`favicon.svg` is the same ball mark (crisp at any size, tiny). An `apple-touch-icon.png` (180×180) covers iOS home-screen/share contexts that don't take SVG.

### Umami, loaded conditionally from a build-time env var
`analytics.ts` reads `import.meta.env.VITE_UMAMI_WEBSITE_ID` (inlined by Vite at build). If unset, it returns immediately and injects nothing — so dev and any unconfigured build are analytics-free. Umami is **cookieless**, so no consent banner is required. The website ID is a **public** client identifier (it appears in the page for every visitor), so it's committed as a literal in `render.yaml` rather than treated as a secret — making the configuration reproducible IaC with no manual dashboard step. An optional `VITE_UMAMI_SRC` overrides the script origin (defaults to Umami Cloud).

## Risks / Trade-offs

- **Static `og:image`** means the card is the same for every URL/view; acceptable for a single marketing surface.
- **Platform caching** delays the new card on previously-shared links until a manual re-scrape; documented, not solvable from our side.
- **Third-party script** adds one async request; mitigated by Umami's small, deferred, cookieless script and by loading nothing when unconfigured.
- **`rsvg-convert` dependency** is build-machine-only (asset generation), not a runtime/site dependency.

## Migration Plan

Additive and static. New `<head>` tags and public assets; one conditional script. No backend, schema, or API changes. Disabling analytics is just clearing the env var and rebuilding.

## Open Questions

- Whether to later add event tracking (e.g. search performed, venue opened) — would argue for PostHog over Umami; out of scope here.
- Whether to add a `robots`/`canonical` pass or a richer `sitemap`; not needed for current reach goals.
