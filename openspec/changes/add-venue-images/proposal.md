## Why

A watch-party finder is a "should I go here?" tool, and people decide partly on how a place looks — is it a proper sports bar, a cozy pub, a big outdoor plaza? Today every venue is text-only. Adding a representative image to each venue (especially in the detail view) makes the list scannable and the choice confident. The hard part is doing it **rights-safely**: we must not scrape Google Images, rehost the venue's own photos, or hotlink third-party thumbnails. We need images we are licensed to display.

## What Changes

A **three-tier image chain**: confirmed Google Places photo → Wikimedia Commons photo → honest SVG category illustration.

- **Tier 1 — Google Places Photos.** Resolve each venue to a Google **`place_id`** (once, via a backfill command), then fetch its photo through a **backend proxy** so the API key stays server-side and we can honor Google's terms (show attribution, don't permanently rehost the bytes, only the `place_id` is stored long-term). A confirm/reject review step promotes ambiguous candidates (see below).
- **Tier 2 — Wikimedia Commons.** For public places not confirmed on the Google tier, resolve a **CC-licensed Commons image** (a stable file URL + required attribution) via the MediaWiki API. Commons needs no API key, so this tier is always-on but **fails closed** (returns nothing on any error). A second backfill command (`resolvevenuewikimedia`) populates it.
- **Tier 3 — category illustration.** When neither photo source yields an image, show a clean, rights-free graphic chosen by `venue_type` (bar, brewery, waterfront, plaza, …). It's honestly generic — it never implies it's a photo of that specific venue.
- **Confirm/reject review.** The Google backfill stores a candidate `place_id` for low-confidence matches but leaves `image_source` blank + `needs_review=True`. A reviewer promotes (`--confirm` / admin "Confirm Google photo match") or discards (`--reject` / admin "Reject match") each candidate; rejection drops the venue to the next tier.
- **Rejected: Unsplash / stock imagery.** Considered and rejected — stock photos misrepresent the specific venue. The fallback is an honest illustration, not a generic stock photo.
- **Model:** add `place_id`, `image_source`, `image_url` (Wikimedia tier), and `image_attribution` to `Venue` (additive, nullable/blank). No image bytes are stored.
- **API:** the venue serializer exposes an `image` block (`{url, attribution, source}` or the fallback), and a proxy endpoint (e.g. `GET /api/venues/<slug>/photo`) streams/redirects to the current Places photo with short-lived caching to bound cost.
- **Backfill:** a `resolvevenueplaces` management command matches each venue by name + address to a `place_id` (Places Text Search / Find Place), flags ambiguous matches for review, and is idempotent.
- **Frontend:** `VenueDetail` shows the image with a required attribution caption; lists/cards and map pins use the lightweight fallback (or a single cached thumbnail) to avoid a Places call per row.
- **Config:** a server-only `GOOGLE_PLACES_API_KEY`, wired in `render.yaml` as a secret (`sync: false`).

## Capabilities

### New Capabilities
- `venue-images`: rights-safe venue imagery via a three-tier chain — a confirmed Google Places photo (served by an attributed proxy), else a CC-licensed Wikimedia Commons photo (with attribution), else a category-illustration fallback. Includes a confirm/reject review step for ambiguous Google matches.

## Impact

- **Schema:** additive `Venue` fields (`place_id`, `image_source`, `image_url`, `image_attribution`); migrations. No stored image bytes.
- **New code:** a photo-proxy view + URL; a `resolvevenueplaces` backfill command (with `--confirm`/`--reject`); an isolated `events.wikimedia` Commons client + `resolvevenuewikimedia` backfill; admin actions for confirm/reject; category-illustration assets; `VenueDetail` image rendering with attribution for both photo sources.
- **External dependency & cost:** Google Places (Place Photos + a Places lookup for backfill) — pay-per-call with a monthly free credit; cost bounded by storing `place_id`, fetching photos mostly on the detail view, and caching/CDN. A `GOOGLE_PLACES_API_KEY` secret is required; the feature degrades to the fallback when unset.
- **Compliance:** attribution always rendered; `place_id` cached long-term, photo bytes not rehosted — per Google Places terms.
- **Tests:** serializer image block (photo vs fallback), proxy behavior when key/place_id missing, backfill matching + idempotency.
