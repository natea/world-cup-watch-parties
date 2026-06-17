## 1. Project foundation

- [x] 1.1 Add a backend dependency manifest (Django, djangorestframework, django-cors-headers, pydantic, psycopg, anthropic) and a virtualenv/uv setup documented in the README
- [x] 1.2 Scaffold the Django project: `config/` settings package (env-driven DB config, PostgreSQL prod + SQLite dev) and an `events` app
- [x] 1.3 Relocate `models.py` → `events/models.py`, `extraction_schema.py` → `events/import_contract.py`; remove the superseded root-level prototype files
- [x] 1.4 Generate and apply the initial migration; verify `migrate` runs clean on a fresh DB and the dev server boots
- [x] 1.5 Register `Team`, `Match`, `Venue`, `VenueAffiliation`, `Screening`, `ScreeningPolicy` in the Django admin with `needs_review` list filters
- [x] 1.6 Add a smoke test asserting the project boots and all six models are registered

## 2. Reference data

- [x] 2.1 Add a `loadreferencedata` management command that upserts teams by `fifa_code` and matches by `fifa_match_number` from a structured source (no LLM), storing kickoff UTC
- [x] 2.2 Support unresolved knockout fixtures: null teams + placeholder labels + stable `bracket_slot`
- [x] 2.3 Seed the two sample matches and teams from `sample_data.json`; document where the full ~104-match fixture list plugs in
- [x] 2.4 Test: idempotent re-run creates no duplicates; an unresolved fixture loads with placeholders and a bracket slot

## 3. Data import

- [x] 3.1 Relocate the importer into `events/management/commands/importwatchparties.py`, validating the payload against the Pydantic contract before any DB write
- [x] 3.2 Upsert venues (by slug), affiliations, screenings (by venue+match+`starts_at`), and policies; preserve `source`/`source_url`/`needs_review`
- [x] 3.3 Materialize screening policies at the end of import, flagging generated screenings (`is_generated=true`)
- [x] 3.4 Wire `extract_with_claude.py` into the app as a (deferred-use) extraction command, unchanged in contract
- [x] 3.5 Test: import `sample_data.json` twice → identical row counts; invalid payload aborts with zero writes; `all_matches` policy fans out; re-materialize after resolving a knockout fixture picks up new `by_team` screenings

## 4. Screening API (DRF)

- [x] 4.1 Add a shared filter parser translating query params → `ScreeningQuerySet` methods (family-friendly, free/paid, indoor/outdoor, venue type, region, exclude-bars)
- [x] 4.2 Implement `/api/schedule`: screenings grouped by local day, ordered by kickoff, with venue + match (resolved-or-placeholder) + cost/access fields
- [x] 4.3 Implement `/api/map`: only venues with coordinates and ≥1 matching screening; optional anchor lat/lng → Haversine distance sort via bounding-box prefilter
- [x] 4.4 Implement `/api/screenings`: team param with "playing" vs "supporter hub" modes, plus shared filters
- [x] 4.5 Serializers expose provenance (`source`, `source_url`, `needs_review`, `updated_at`) and always emit TBD-safe match labels
- [x] 4.6 Configure `django-cors-headers` for the Vite dev origin
- [x] 4.7 Tests: each endpoint honors the same filter set identically; family-friendly excludes the post-cutoff screening at the evening-cutoff venue; free toggle includes free-lottery/free-minimum; PostgreSQL DB filter and Python fallback agree

## 5. Web client (React + Vite + TS)

- [x] 5.1 Scaffold `frontend/` with Vite + React + TypeScript; add a typed API client and an env-configured API base URL
- [x] 5.2 Implement a single shared, URL-synced filter store consumed by all three views
- [x] 5.3 Build the schedule view: day-grouped, kickoff-ordered list rendering local time from UTC
- [x] 5.4 Build the map view with react-leaflet + OSM tiles: plot only matching venues, pin popups show the venue's relevant screening(s)
- [x] 5.5 Build the team ("alliance") view: multi-team selection resolving to "matches featuring team" and/or "supporter-hub venues", with the two senses visibly distinct
- [x] 5.6 Render TBD matchups via placeholder labels in all three views; show provenance + last-updated + needs-review indicator on detail
- [x] 5.7 Verify end-to-end against the seeded backend: switching views preserves filters and results stay consistent across schedule/map/team

## 6. End-to-end seed & docs

- [x] 6.1 Document the one-command-ish seed flow: `migrate` → `loadreferencedata` → `importwatchparties sample_data.json`
- [x] 6.2 README: run backend + frontend dev servers, env vars, SQLite-vs-PostgreSQL note, and the family-friendly backend caveat
- [x] 6.3 Manual acceptance pass against the sample data exercising every PRD edge case (Fan Fest free-lottery, evening 21+ cutoff, all-matches policy, supporter-hub affiliation, TBD knockout)

## 7. Post-v1 enhancements

- [x] 7.1 Expand reference data: the 7 Gillette fixtures + the nations playing there, plus USA/Brazil/Croatia so supporter-hub affiliations resolve (provisional FIFA numbers flagged for the authoritative list)
- [x] 7.2 Extract the full research corpus (`data/world-cup-watch-parties.md`) into a validated bundle (`data/watch_parties.json`, ~49 venues with affiliations/policies); point the seed flow at it; keep `sample_data.json` as the test fixture
- [x] 7.3 Local date affordances: show the local date alongside kickoff in map popups, team, and venue-detail contexts
- [x] 7.4 Venue detail: add `/api/venues/<slug>/` (profile + affiliations + ordered screenings, 404 on unknown) with tests
- [x] 7.5 Venue detail page in the client (URL-driven, shareable), reachable from every view, with an external map link, affiliations, provenance, and a back action that preserves prior view/filters
- [x] 7.6 Game-grouped (DRY) listing: group screenings by match in the schedule and the team "playing" column — matchup/time shown once as a header, venues listed beneath
- [x] 7.7 Polish: proper Scotland/England subdivision flag emojis; de-duplicated affiliation flag rendering
