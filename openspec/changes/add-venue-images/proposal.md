## Why

A watch-party finder is a "should I go here?" tool, and people decide partly on how a place looks — is it a proper sports bar, a cozy pub, a big outdoor plaza? Today every venue is text-only. Adding a representative image to each venue (especially in the detail view) makes the list scannable and the choice confident. The hard part is doing it **rights-safely**: we must not scrape Google Images, rehost the venue's own photos, or hotlink third-party thumbnails. We need images we are licensed to display.

## What Changes

- **Primary source — Google Places Photos.** Resolve each venue to a Google **`place_id`** (once, via a backfill command), then fetch its photo through a **backend proxy** so the API key stays server-side and we can honor Google's terms (show attribution, don't permanently rehost the bytes, only the `place_id` is stored long-term).
- **Fallback — category illustration.** When a venue has no usable place photo, show a clean, rights-free graphic chosen by `venue_type` (bar, brewery, waterfront, plaza, …), generated like our other brand assets. It's honestly generic — it never implies it's a photo of that specific venue.
- **Model:** add `place_id`, `image_source`, and `image_attribution` to `Venue` (additive, nullable/blank). No image bytes are stored.
- **API:** the venue serializer exposes an `image` block (`{url, attribution, source}` or the fallback), and a proxy endpoint (e.g. `GET /api/venues/<slug>/photo`) streams/redirects to the current Places photo with short-lived caching to bound cost.
- **Backfill:** a `resolvevenueplaces` management command matches each venue by name + address to a `place_id` (Places Text Search / Find Place), flags ambiguous matches for review, and is idempotent.
- **Frontend:** `VenueDetail` shows the image with a required attribution caption; lists/cards and map pins use the lightweight fallback (or a single cached thumbnail) to avoid a Places call per row.
- **Config:** a server-only `GOOGLE_PLACES_API_KEY`, wired in `render.yaml` as a secret (`sync: false`).

## Capabilities

### New Capabilities
- `venue-images`: rights-safe venue imagery — actual Google Places photos resolved by `place_id` and served via an attributed backend proxy, with a category-illustration fallback when no licensed photo is available.

## Impact

- **Schema:** additive `Venue` fields (`place_id`, `image_source`, `image_attribution`); a migration. No stored image bytes.
- **New code:** a photo-proxy view + URL; a `resolvevenueplaces` backfill command; category-illustration assets + generator; `VenueDetail` image rendering with attribution.
- **External dependency & cost:** Google Places (Place Photos + a Places lookup for backfill) — pay-per-call with a monthly free credit; cost bounded by storing `place_id`, fetching photos mostly on the detail view, and caching/CDN. A `GOOGLE_PLACES_API_KEY` secret is required; the feature degrades to the fallback when unset.
- **Compliance:** attribution always rendered; `place_id` cached long-term, photo bytes not rehosted — per Google Places terms.
- **Tests:** serializer image block (photo vs fallback), proxy behavior when key/place_id missing, backfill matching + idempotency.
