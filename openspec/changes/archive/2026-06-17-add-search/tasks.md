## 1. Search endpoint

- [x] 1.1 Add `SearchView` (`GET /api/search/?q=`) in `events/views.py` and register it in `events/urls.py`
- [x] 1.2 Query candidates: `Venue` on `name`/`city`/`notes`, `Team` on `name`/`fifa_code`, `VenueAffiliation` on `club` + affiliated `team__name`; use `__istartswith`/`__icontains` (case-insensitive, dev+prod parity)
- [x] 1.3 Build typed suggestions `{type, label, sublabel, target}` where `target` is `{kind:"venue", slug}` or `{kind:"team", code}`; de-duplicate venues that match on multiple fields
- [x] 1.4 Rank in Python (name/code prefix → whole-word → name substring → description substring), then cap to a max (default 10); enforce a minimum query length (return empty below it)
- [x] 1.5 Add a small suggestion serializer (or inline dict shaping) consistent with existing serializers

## 2. Search UI

- [x] 2.1 Add `api.search(q)` to `frontend/src/api.ts` and a `Suggestion` type to `types.ts`
- [x] 2.2 Build `SearchBox` component: debounced input (~150 ms), `AbortController` to cancel stale requests, min-length gate, dropdown render
- [x] 2.3 Keyboard support: ↑/↓ highlight, Enter select, Esc dismiss; click-to-select; close on outside click/blur
- [x] 2.4 Wire selection to existing state via `useFilters`: venue → `openVenue(slug)`; team → `setFilter("team", code)` + `setView("team")` (URL stays in sync)
- [x] 2.5 Place `SearchBox` in the `App.tsx` header next to the tabs; ensure selecting clears any open venue appropriately

## 3. Tests & docs

- [x] 3.1 Endpoint tests: venue-by-name, country-by-name and by-FIFA-code, hub-by-club/affiliation, description-keyword match, ranking order, result cap, and short/empty query → empty
- [x] 3.2 Confirm the dev (SQLite) matching path returns expected results in the test suite
- [x] 3.3 Update README (and the API endpoint table) with the `/api/search/` endpoint and the search box; note the PostgreSQL trigram/full-text upgrade path as future work
