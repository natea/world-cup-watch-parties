## 1. Model & config

- [x] 1.1 Add `place_id`, `image_source`, `image_attribution` (nullable/blank) to `Venue`; make the migration
- [x] 1.2 Add a server-only `GOOGLE_PLACES_API_KEY` setting (env-driven; absent → feature disabled); document it
- [x] 1.3 Wire `GOOGLE_PLACES_API_KEY` in `render.yaml` as a secret (`sync: false`)

## 2. Category-illustration fallback

- [x] 2.1 Generate a clean, rights-free illustration per `VenueType` (extend the asset generator); store under `frontend/public/`
- [x] 2.2 Map `venue_type` → fallback asset URL; ensure it reads as generic, not a venue photo

## 3. Photo proxy & serializer

- [x] 3.1 Add `GET /api/venues/<slug>/photo` proxy: server-side key, fetch Place Photo, 302/stream; short-lived cache; fall back on missing key/place_id/error
- [x] 3.2 Add an `image` object to `VenueSerializer`: `{url, attribution, source}` (photo → proxy url + attribution; else fallback url + null attribution + `source="fallback"`)
- [x] 3.3 Ensure attribution text is captured from the Places photo metadata and surfaced via the serializer

## 4. Backfill command

- [x] 4.1 Add `resolvevenueplaces`: match each venue by name + address/city via Places Text Search/Find Place; write `place_id` + `image_source`
- [x] 4.2 Flag low-confidence/ambiguous matches with `needs_review=True`; idempotent (skip resolved unless `--refresh`); no-op without the API key

## 4b. Confirm/reject review & Wikimedia tier

- [x] 4b.1 Add `image_url` (blank URLField) to `Venue` for the Wikimedia tier; migration (Google stays proxy-resolved, does not use it)
- [x] 4b.2 Extend `resolvevenueplaces` with `--confirm <slug> …` (promote to `google_places`, resolve+store attribution, clear `needs_review`; no-op cleanly without key) and `--reject <slug> …` (clear candidate `place_id` + `needs_review` → next tier)
- [x] 4b.3 Add Django admin actions on `Venue`: "Confirm Google photo match" / "Reject match" for multi-select review
- [x] 4b.4 Add isolated `events/wikimedia.py` Commons client: `find_image(name, city, lat, lng) -> WikiImage|None`; free-license gate; HTTP behind a private `_get` seam; fails closed (returns `None`) on any error; no new pip dependency
- [x] 4b.5 Add `resolvevenuewikimedia` backfill: store `image_url` + `image_attribution` + `image_source="wikimedia"` on a confident hit; idempotent (skip google/wikimedia unless `--refresh`); `--dry-run`
- [x] 4b.6 Extend serializer `get_image` to three tiers (google_places → wikimedia → fallback)

## 5. Frontend

- [x] 5.1 Render the venue image in `VenueDetail` with an attribution caption shown whenever `attribution` is present (both `google_places` and `wikimedia`)
- [x] 5.2 Use the fallback (or a cached thumbnail) in lists/cards/map pins — no per-row photo proxy calls
- [x] 5.3 Add the `image` shape to `types.ts`; handle load errors by swapping to the fallback

## 6. Tests & docs

- [x] 6.1 Serializer tests: photo case (with attribution) vs fallback case (by venue type, no attribution)
- [x] 6.2 Proxy tests: returns fallback when key/place_id missing; does not rehost bytes
- [x] 6.3 Backfill tests: confident match stored + idempotent; ambiguous match flagged for review (mock the Places client — no live calls)
- [x] 6.4 README: document the image feature, `GOOGLE_PLACES_API_KEY`, the backfill command, attribution/caching compliance, and the no-key fallback behavior
- [x] 6.5 Tests (mocked, no live network): serializer wikimedia tier; `--confirm` promotes a flagged candidate / `--reject` clears it to fallback; Wikimedia backfill stores a hit + idempotent + no-ops to fallback on no result; wikimedia client free-license gate + fail-closed
