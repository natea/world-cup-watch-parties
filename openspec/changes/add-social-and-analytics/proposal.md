## Why

The deployed site had no shareable identity and no way to measure reach:

- Pasting `worldcup.stagehopper.app` into LinkedIn, X, Facebook, iMessage, or Slack produced a bare link — no title, image, or description — because `index.html` shipped a generic `<title>frontend</title>` and zero Open Graph/Twitter tags. The favicon was a leftover purple bolt, not on-brand.
- There was no analytics, so visitor counts were unknown.

This change was implemented first and is captured here retroactively so the brand/share/analytics behavior lives in the spec.

## What Changes

- **Social preview metadata** in `index.html`: a real title and description, full **Open Graph** tags (`og:title`/`description`/`type`/`url`/`site_name`/`image` + dimensions/alt) and **Twitter Card** tags (`summary_large_image`), plus `theme-color`, so links unfurl with an image and teaser across major platforms.
- A **1200×630 social card** (`og-image.png`) on the app's dark theme: soccer ball, "MA World Cup 2026 — Watch-Party Finder", a one-line description, and the URL, referenced by an absolute `og:image` URL.
- A **soccer-ball favicon** (`favicon.svg`) replacing the placeholder bolt, plus an `apple-touch-icon.png`.
- A reproducible generator, `scripts/make_social_assets.py`, that renders the favicon and OG card from computed SVG via `rsvg-convert`.
- **Privacy-first analytics** via **Umami (cloud)**: a small loader (`frontend/src/analytics.ts`) that injects the Umami script **only when `VITE_UMAMI_WEBSITE_ID` is set**, so dev and unconfigured builds send no traffic. The production website ID is wired in `render.yaml` (a public client-side identifier, committed as a literal).

## Capabilities

### New Capabilities
- `social-and-analytics`: rich link-unfurl metadata with a branded social card and favicon, plus opt-in, privacy-first visitor analytics that is inert unless configured.

## Impact

- **New files:** `frontend/public/og-image.png`, `frontend/public/apple-touch-icon.png`, `frontend/src/analytics.ts`, `scripts/make_social_assets.py`.
- **Edited:** `frontend/index.html` (title/description/OG/Twitter/icons), `frontend/public/favicon.svg` (soccer ball), `frontend/src/main.tsx` (calls the analytics loader), `render.yaml` (`VITE_UMAMI_WEBSITE_ID`).
- **No backend or schema changes**; static assets served by the existing Render static site.
- **Privacy:** Umami is cookieless and needs no consent banner; analytics is fully disabled when the env var is unset.
- **Caveat:** platforms cache unfurl data, so already-shared links need a re-scrape via each platform's debugger to pick up the new card.
