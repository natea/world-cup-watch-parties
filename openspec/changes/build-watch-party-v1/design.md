## Context

The watch-party finder has a validated data-model prototype (`models.py`, `extraction_schema.py`, `import_watch_parties.py`, `extract_with_claude.py`) and a `sample_data.json` that exercises the edge cases the PRD calls out (Fan Festival free-lottery cost, a venue that flips to 21+ at 8pm, an "all matches" policy, supporter-hub affiliations). None of it is wired into a runnable Django project, there is no API, and there is no UI.

This change builds v1: a runnable Django + DRF backend and a React + Vite SPA, app-first against seed data. The full LLM extraction of the ~150-venue corpus and human review are explicitly deferred; the import pipeline is wired and seeded from `sample_data.json` so the app is end-to-end real without the corpus run.

Constraints carried from the PRD: PostgreSQL is the production target (the family-friendly DB predicate is verified there); times are stored UTC and rendered local; the three views are projections of the one `Screening` spine, so filters must be defined once and shared.

## Goals / Non-Goals

**Goals:**
- A Django project that boots, migrates, and serves the relocated prototype models unchanged in behavior.
- Reference-data load (teams + fixtures) kept strictly separate from extracted data.
- Idempotent import seeded from `sample_data.json`, finishing with policy materialization.
- DRF endpoints for schedule/map/screenings with one shared, composable filter layer over the Screening queryset.
- A React + Vite + TypeScript SPA with schedule, map, and team views sharing one filter set, handling TBD matchups and showing provenance.

**Non-Goals:**
- Running full LLM extraction + human review over the research corpus (deferred follow-up).
- Ticketing/transactions, user accounts, real-time capacity, personalization, non-MA coverage.
- PostGIS / GeoDjango — the Haversine + bounding-box approach is sufficient at ~150 venues.

## Decisions

**Project layout — single repo, two workspaces.** A Django project at the repo root (`config/` settings package + `events/` app) plus a `frontend/` React+Vite workspace. Rationale: keeps the proven Python alongside the new client without a premature monorepo tool; matches the PRD's "separate client consuming the API." Alternative considered: Django-templates+HTMX (one codebase, faster) — rejected because the user chose a React SPA for a richer map/UX and a clean API boundary.

**Relocate, don't rewrite, the prototype.** Move `models.py` → `events/models.py`, `extraction_schema.py` → `events/import_contract.py`, and the importer/extractor into `events/management/commands/`. Generate the initial migration from the existing model definitions. Rationale: the model is the validated core of the PRD; rewriting it risks regressing the three hard-won modeling decisions (cost enum, time-dependent age, affiliation-as-entity). Alternative: re-derive models — rejected as needless risk.

**Filters live in the queryset, exposed via DRF, mirrored in the client.** The `ScreeningQuerySet` already implements `free/paid/indoor/outdoor/venue_type/exclude_bars/family_friendly/for_team/at_supporter_hub`. The API layer is a thin translation of query params → these queryset methods; serializers shape the three view responses. The React client holds the active filter set in one store (URL-synced) and passes it to every endpoint. Rationale: one definition of each filter, honored identically across views, exactly as the PRD's "one model, three projections" demands. Alternative: per-view bespoke filtering — rejected as the drift the PRD warns against.

**Three endpoints, not one generic one.** `/api/schedule` (day-grouped), `/api/map` (venues-with-matching-screenings, optional anchor for distance), `/api/screenings` (team mode + filters). They share the filter parser and the underlying queryset; only the serialization/grouping differs. Rationale: endpoints map ~1:1 onto queryset methods (PRD §10) and keep the client simple.

**Family-friendly predicate: DB filter on PostgreSQL, Python fallback on SQLite.** Use the existing `family_friendly()` `Case/When` annotation when the backend supports comparing `starts_at__time` to the `evening_cutoff` column; fall back to filtering by the per-row `is_family_friendly` property otherwise. Local dev may use SQLite; CI and prod use PostgreSQL.

**Map rendering: Leaflet + react-leaflet, OpenStreetMap tiles.** No API key, no billing, fine for ~150 pins. Alternative: Mapbox/Google — rejected for v1 (keys, cost, overkill).

**Seed flow.** `migrate` → `loadreferencedata` (teams + fixtures, incl. the two sample matches and a path to the full fixture list) → `importwatchparties sample_data.json` (which materializes policies). This gives a populated, demoable app from a clean checkout.

## Risks / Trade-offs

- **Sample data is thin (4 venues, 2 matches).** → The app is correct but sparse; the three views and all filter edge cases are still demonstrable because the sample was built to exercise them. Full corpus is a deferred follow-up, explicitly scoped out of v1.
- **SQLite vs PostgreSQL divergence on the family-friendly filter.** → Pin PostgreSQL for CI and any deployed environment; document the SQLite Python-fallback path; add a test asserting both code paths agree on the sample's evening-cutoff venue.
- **Reference fixture source not yet identified.** → v1 loads the two sample matches plus whatever authoritative fixture list is provided; the command is written to upsert by `fifa_match_number` so loading the full ~104-match list later is a no-migration data step. (Open question below.)
- **CORS / two dev servers.** → Add `django-cors-headers` allowing the Vite dev origin; document running both servers. Acceptable cost of the SPA choice.
- **TBD matchups in the UI.** → Serializers always emit resolved-or-placeholder labels; the client renders placeholders; a test covers a null-team match end-to-end.

## Migration Plan

This is greenfield application code; there is no production data to migrate. Deploy = stand up PostgreSQL, run `migrate`, run `loadreferencedata`, run `importwatchparties`. Rollback = drop/recreate the database and redeploy the prior build; the import is idempotent so re-seeding is safe. The standalone prototype `.py` files at the repo root are superseded by their relocated copies and removed in this change.

## Open Questions

- What is the authoritative structured source for the full FIFA fixture list (teams + ~104 matches), and in what format will it be supplied?
- Should local development default to SQLite (zero-setup) or PostgreSQL via Docker (parity with prod)? Leaning SQLite for dev ergonomics with a documented PostgreSQL path.
- Does v1 need any deployment target wired (e.g. a single container), or is "runs locally end-to-end" the v1 bar? Assumed local-only for v1 unless specified.
