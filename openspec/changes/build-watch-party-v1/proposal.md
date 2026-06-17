## Why

The data model, extraction contract, and idempotent importer for the Massachusetts World Cup 2026 watch-party finder exist as a validated prototype (loose Python files), but there is no runnable application: no Django project to host the models, no API to query them, and no frontend to present the schedule, map, and team views the PRD specifies. With the tournament running June 11 – July 19, 2026, v1 needs to turn the proven model into a working end-to-end product that a fan can actually use.

## What Changes

- Stand up a real Django project and `events` app, moving the prototype `models.py`, `extraction_schema.py`, importer, and extraction script into it as first-class, migrated modules.
- Add a Django management command to load reference data (teams + the canonical FIFA fixture list) from an authoritative structured source, kept separate from LLM-extracted venue data.
- Wire the idempotent import command and policy materialization into the Django project, seeded from `sample_data.json` for v1.
- Build a Django REST Framework API exposing three endpoints that map onto the Screening queryset spine: schedule, map, and screenings (team + filter parameters), with composable filters (family-friendly, free/paid, indoor/outdoor, venue type, region).
- Build a React + Vite + TypeScript single-page client rendering the three first-class views (schedule list, interactive Leaflet map, team-centric "alliance" view) against the API, sharing one active filter set across all views.
- Expose source provenance and `needs_review`/`last updated` data through the API and surface it in the UI.
- **Non-goals for v1 (deferred):** full LLM extraction of the complete ~150-venue corpus and human review, ticketing/transactions, user accounts, real-time capacity, and coverage beyond Massachusetts.

## Capabilities

### New Capabilities
- `project-foundation`: Django project + `events` app scaffold, settings, migrations, and relocation of the prototype model/schema/importer into a runnable, tested package.
- `reference-data`: Authoritative load of teams and the FIFA fixture list (including nullable knockout fixtures with bracket slots) via a dedicated management command, distinct from extracted data.
- `data-import`: Idempotent upsert importer driven by the Pydantic contract, seeded from `sample_data.json`, finishing by materializing screening policies into concrete screenings.
- `screening-api`: DRF endpoints for the schedule, map, and team/screenings views with composable, view-shared filters over the Screening spine.
- `web-client`: React + Vite + TypeScript SPA presenting the schedule, map, and team views with a shared filter set and provenance display.

### Modified Capabilities
<!-- None — this is the first change; no existing specs in openspec/specs/. -->

## Impact

- **New code:** Django project package, `events` app (models, admin, serializers, views, urls, management commands, migrations), `requirements`/dependency manifest, and a `frontend/` React+Vite workspace.
- **Relocated code:** `models.py`, `extraction_schema.py`, `import_watch_parties.py`, `extract_with_claude.py` move into the app; the standalone prototype files are superseded.
- **Dependencies (backend):** Django, djangorestframework, django-cors-headers, pydantic, psycopg (PostgreSQL target), Anthropic SDK (extraction, deferred-use). **(frontend):** React, Vite, TypeScript, a map library (Leaflet/react-leaflet), a data-fetching client.
- **Data:** PostgreSQL assumed for production (family-friendly DB predicate); SQLite acceptable for local dev with the Python predicate fallback. Seed source is `sample_data.json` + reference fixture data.
- **APIs:** New public read endpoints (`/api/schedule`, `/api/map`, `/api/screenings`) consumed by the SPA.
