## Context

Venues are real Massachusetts businesses (bars, breweries, plazas, hotels). The only rights-safe way to show what they look like, at scale, without an outreach/UGC program, is a Places API whose terms permit in-app display. Google Places is the chosen primary source. Its terms shape the architecture more than anything else: we may store the **`place_id`** indefinitely, must **render attribution** with each photo, and must **not permanently rehost** the photo bytes. The frontend already has a `VenueDetail` view and a generated-asset pipeline (`scripts/make_social_assets.py`) we can mirror for fallbacks.

## Goals / Non-Goals

- **Goals:** a recognizable image per venue where one exists; strict ToS compliance (attribution, no rehosting, only `place_id` persisted); graceful, honest fallback; bounded API cost; feature works with or without the API key.
- **Non-goals:** an image gallery/carousel, user uploads (a separate future capability), AI-generated venue photos (would misrepresent the place), and pixel-perfect art direction.

## Decisions

### Store the `place_id`, proxy the photo
We persist `place_id` (allowed long-term) and resolve the actual photo on demand through a **backend proxy** (`GET /api/venues/<slug>/photo`). The proxy holds the `GOOGLE_PLACES_API_KEY` (never shipped to the client), calls the Place Photos endpoint, and 302-redirects to (or streams) the photo URL. This keeps the key server-side, centralizes attribution/caching policy, and sidesteps CORS. Photo bytes are not written to our storage.

### Cost control: where and how often we call
- **Lists, map pins, cards** do **not** trigger a Places call per row — they use the category-illustration fallback (or a single small cached thumbnail per venue). The full photo loads on the **detail view** only.
- **Short-lived caching** of the resolved photo URL/`photo_reference` (within ToS) plus CDN/browser caching on the proxy response bounds repeat cost.
- Backfill resolves `place_id` **once** (cached forever), so steady-state cost is only photo fetches, not lookups.

### Backfill via a management command
`resolvevenueplaces` matches each venue by `name` + `address`/`city` using Places Text Search / Find Place, writes `place_id` and `image_source="google_places"`, and sets `needs_review=True` on low-confidence/ambiguous matches (reusing the existing review flag and admin filter). Idempotent: skips venues that already have a `place_id` unless `--refresh`.

### Honest fallback by `venue_type`
When a venue has no `place_id` or the photo fetch fails, the serializer returns a fallback image keyed by `venue_type`, rendered as a clean rights-free illustration (generated like the brand assets). It is visually distinct from a photo so users aren't misled into thinking it's the actual place.

### Serializer shape
`VenueSerializer` gains an `image` object: `{ "url": <proxy or fallback url>, "attribution": <text|null>, "source": "google_places"|"fallback" }`. The client renders the caption only when `attribution` is present. Keeping it one nested object means the frontend has a single, uniform thing to render.

### Key handling and graceful degradation
`GOOGLE_PLACES_API_KEY` is a server-only secret (`sync: false` in `render.yaml`). When it's unset (local dev, un-configured deploys), the proxy and backfill no-op and every venue uses the fallback — the feature is additive and never breaks a build or a page.

## Risks / Trade-offs

- **Per-photo cost / quota.** Mitigated by detail-view-only fetches, caching, and storing `place_id`. A quota cap + fallback-on-error keeps a spike from breaking pages.
- **Wrong-venue match** in backfill (two "The Tavern"s). Mitigated by name+address matching and `needs_review` triage in admin; never auto-publish a low-confidence match as definitive.
- **ToS drift.** Centralizing all Places access behind one proxy + one backfill command means attribution/caching rules live in one place if terms change.
- **Latency** of an extra hop for the photo. Acceptable on the detail view; the proxy redirects rather than buffering when possible.

## Migration Plan

1. Migration adds the three nullable/blank `Venue` fields — safe on existing rows (all default to fallback).
2. Generate the category-illustration assets.
3. Ship serializer `image` block + proxy + `VenueDetail` rendering (everything shows fallback until backfilled).
4. Set `GOOGLE_PLACES_API_KEY`; run `resolvevenueplaces`; review flagged matches in admin.

Each step is independently deployable; the UI is correct at every stage (fallback first, photos as `place_id`s land).

## Open Questions

- Cache TTL for resolved photos within Google's terms — pick the longest compliant window to minimize cost.
- Whether to also surface a Street View image (storefront "find the door") as a secondary slot, or keep a single image for v1 (lean: single image now).
- Whether list/map thumbnails are worth one cached small photo per venue, or fallback-only there (lean: fallback-only first, measure).
