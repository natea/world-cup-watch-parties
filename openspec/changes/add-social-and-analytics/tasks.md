<!-- Implemented ahead of this retroactive proposal; all boxes reflect work already on disk and deployed. -->

## 1. Brand assets

- [x] 1.1 Add `scripts/make_social_assets.py` that computes the soccer-ball geometry and composes the 1200×630 card, rasterizing with `rsvg-convert`
- [x] 1.2 Generate `frontend/public/favicon.svg` (soccer ball), `og-image.png` (1200×630), and `apple-touch-icon.png` (180×180)

## 2. Social metadata

- [x] 2.1 Set a descriptive `<title>` and meta description in `frontend/index.html`
- [x] 2.2 Add Open Graph tags (title, description, type, url, site_name, image + width/height/alt) with an absolute `og:image` URL
- [x] 2.3 Add Twitter Card tags (`summary_large_image`, title, description, image) and `theme-color`
- [x] 2.4 Link the SVG favicon and the Apple touch icon

## 3. Analytics

- [x] 3.1 Add `frontend/src/analytics.ts` that injects the Umami script only when `VITE_UMAMI_WEBSITE_ID` is set (optional `VITE_UMAMI_SRC` override; defaults to Umami Cloud)
- [x] 3.2 Call `initAnalytics()` from `frontend/src/main.tsx`
- [x] 3.3 Wire `VITE_UMAMI_WEBSITE_ID` in `render.yaml` (public client identifier, committed as a literal)

## 4. Verification

- [x] 4.1 Build inlines the Umami script with the website ID; unconfigured build injects nothing
- [x] 4.2 Deployed HTML exposes the new title + OG/Twitter tags; `og-image.png` serves `200 image/png` at 1200×630
- [x] 4.3 Confirmed the live bundle contains the Umami loader after deploy
