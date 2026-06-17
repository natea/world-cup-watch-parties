# Massachusetts World Cup 2026 — Watch-Party Finder

Find where to watch the 2026 FIFA Men's World Cup across Massachusetts, three
ways over one dataset: a **schedule**, a **map**, and a **by-team** view, with
composable filters (family-friendly, free/paid, indoor/outdoor, venue type,
region). See [`PRD.md`](./PRD.md) for the full product rationale.

This is **v1**: a runnable Django + DRF backend and a React + Vite client,
seeded from `sample_data.json`. The full LLM extraction of the statewide venue
corpus is wired in (`extractwithclaude`) but deferred — the app runs end-to-end
on the sample, which is built to exercise every modeling edge case.

## Architecture

- **Backend** — Django 6 + Django REST Framework. The atomic unit is a
  `Screening` (a venue showing a match at a time); the three views are
  projections of one `ScreeningQuerySet`, and every filter is a composable
  constraint over it (`events/filters.py`).
- **Frontend** — React + Vite + TypeScript SPA (`frontend/`) with a single,
  URL-synced filter set shared across all three views.
- **Data tooling** — a Pydantic import contract (`events/import_contract.py`),
  an idempotent importer, a reference-data loader, and a deferred-use LLM
  extractor, all as Django management commands.

## Prerequisites

- Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/)
- Node ≥ 20 (the frontend was built with [bun](https://bun.sh); npm works too)

## Backend setup

```bash
uv sync                       # core deps (Django, DRF, pydantic, ...)
# optional extras:
uv sync --extra extract       # + anthropic, for the LLM extraction pipeline
uv sync --extra postgres      # + psycopg, for PostgreSQL
```

### Seed the database (the v1 flow)

```bash
uv run python manage.py migrate
uv run python manage.py loadreferencedata             # teams + 7 Gillette fixtures (no LLM)
uv run python manage.py importwatchparties data/watch_parties.json
```

`data/watch_parties.json` is the richer seed — ~49 venues across Massachusetts
(soccer bars by national-team/club affiliation, the Fan Festival, brewery and
waterfront screenings, hotels, and free municipal watch parties), extracted from
[`data/world-cup-watch-parties.md`](./data/world-cup-watch-parties.md). The
smaller `sample_data.json` (4 venues) is kept as a minimal fixture for the test
suite. Either can be imported; they merge idempotently by slug.

`importwatchparties` validates the payload against the Pydantic contract, upserts
every record by its natural key (idempotent — safe to re-run), and finishes by
**materializing screening policies** (e.g. a bar's "shows every match" rule fans
out into concrete screenings). To load the full ~104-match fixture list later,
pass an authoritative file: `loadreferencedata --path fixtures.json`.

### Run the API

```bash
uv run python manage.py runserver 8000
```

Endpoints (all honor the same query-param filter set):

| Endpoint           | View      | Notable params                              |
| ------------------ | --------- | ------------------------------------------- |
| `GET /api/schedule/` | Schedule  | day-grouped, kickoff-ordered                |
| `GET /api/map/`      | Map       | `lat`,`lng` → distance sort                 |
| `GET /api/screenings/` | By team | `team=FRA`, `team_mode=playing\|hub`        |
| `GET /api/teams/`    | —         | team list for the UI                        |
| `GET /api/meta/`     | —         | filter vocabularies for the UI              |

Shared filter params: `cost=free\|paid`, `environment=indoor\|outdoor`,
`venue_type` (csv), `region`, `exclude_bars=true`, `family_friendly=true`,
`day=YYYY-MM-DD`, `upcoming=true`.

Admin (review flagged records): `uv run python manage.py createsuperuser`, then
`/admin/` — venues/screenings have a **needs_review** list filter.

## Frontend setup

```bash
cd frontend
bun install        # or: npm install
bun run dev        # or: npm run dev  → http://localhost:5173
```

The API base URL is configured in `frontend/.env` (`VITE_API_BASE`,
defaults to `http://localhost:8000/api`). Run the backend on `:8000` and the
frontend on `:5173`; CORS is preconfigured for that origin.

## Configuration

Environment variables (optional; sensible dev defaults):

| Variable               | Default                                       | Notes                               |
| ---------------------- | --------------------------------------------- | ----------------------------------- |
| `DATABASE_URL`         | _(unset → SQLite `db.sqlite3`)_               | `postgres://user:pass@host/db`      |
| `DJANGO_SECRET_KEY`    | dev key                                       | set in production                   |
| `DJANGO_DEBUG`         | `true`                                        |                                     |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver`              |                                     |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` |                                     |

### SQLite vs PostgreSQL — the family-friendly caveat

"Family-friendly" is **time-dependent**: some venues are all-ages by day and
21+ after an evening cutoff, so it is a predicate over *(venue, screening time)*,
not a venue flag. On **PostgreSQL** this is evaluated as a database-level
`Case/When` filter. On **SQLite** (the zero-setup dev default) the app falls back
to the per-row Python predicate (`Screening.is_family_friendly`, the canonical
source of truth). Both paths agree; PostgreSQL is the assumed production
database. The active path is chosen automatically from `settings.USING_POSTGRES`.

## Deployment (Render.com)

The repo ships a [`render.yaml`](./render.yaml) Blueprint that provisions three
resources in one shot:

| Resource       | Type            | URL                                  |
| -------------- | --------------- | ------------------------------------ |
| `worldcup-api` | Django web svc  | `worldcup-api.onrender.com` (default) |
| `worldcup-web` | Static site     | `worldcup.stagehopper.app` (custom)  |
| `worldcup-db`  | PostgreSQL      | internal `DATABASE_URL`              |

The API runs under gunicorn and serves its own admin/DRF assets via WhiteNoise;
the React app is a CDN-hosted static site whose `VITE_API_BASE` is baked at
build time from the API service's host. PostgreSQL is used in production, so the
DB-level family-friendly filter is active (see caveat below).

**First deploy:**

1. Push this repo to GitHub.
2. In `render.yaml`, set the `repo:` URL on the `worldcup-api` service to your
   GitHub repo (or remove the line and connect the repo in the dashboard).
3. Render Dashboard → **New → Blueprint** → select the repo → **Apply**.
   `build.sh` runs `collectstatic`, `migrate`, and the idempotent seed loaders
   (`loadreferencedata` + `importwatchparties`), so the DB comes up populated.
4. On the `worldcup-web` service → **Settings → Custom Domains**, add
   `worldcup.stagehopper.app` and point that CNAME at the value Render shows.

Production env vars are declared in the Blueprint: `DJANGO_SECRET_KEY`
(auto-generated), `DJANGO_DEBUG=false`, `DATABASE_URL` (from the DB),
`CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`. `ALLOWED_HOSTS` /
`CSRF_TRUSTED_ORIGINS` automatically include the Render hostname via
`RENDER_EXTERNAL_HOSTNAME`. When `DEBUG=false`, settings also enable HTTPS
redirect, secure cookies, HSTS, and the proxy SSL header — all skipped in dev so
local plain-HTTP `runserver` is unaffected.

## Tests

```bash
uv run pytest
```

Covers: project boot + model registration, idempotent reference/import loads,
policy materialization (incl. re-materialize after a knockout fixture resolves),
and all three API endpoints honoring an identical filter set (family-friendly
excludes 21+ bars, the free toggle includes free-lottery, TBD matchups
serialize).

## Project layout

```
config/          Django project (settings, urls, wsgi/asgi)
events/          the app: models, serializers, filters, views, admin
  management/commands/   loadreferencedata · importwatchparties · extractwithclaude
  import_contract.py     Pydantic import/extraction contract
  tests/                 pytest suite
frontend/        React + Vite + TS client (schedule / map / team views)
sample_data.json v1 seed payload (exercises every edge case)
PRD.md           product requirements
openspec/        the spec-driven change that produced this build
```
