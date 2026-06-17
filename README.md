# WorldCup Watcher — Massachusetts 2026

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
uv run python manage.py loadreferencedata --path data/fifa_reference.json   # 104 matches, 48 teams
uv run python manage.py importwatchparties data/watch_parties.json
```

`data/fifa_reference.json` is the **authoritative FIFA 2026 fixture list** (all
104 matches, 48 teams) — `loadreferencedata` loads it by default. It is a
committed snapshot produced by `manage.py fetchfixtures`, which fetches FIFA's
v3 calendar API (`api.fifa.com/api/v3/calendar/matches`, `idSeason=285023` — an
undocumented endpoint discovered by reverse-engineering the fixtures page's
network traffic). Refresh it any time with `manage.py fetchfixtures` (e.g. as
the knockout bracket resolves), then re-run the loaders. Pass `--builtin` to
`loadreferencedata` for the minimal in-code demo seed (7 provisional Gillette
fixtures) used by the test suite.

`data/watch_parties.json` is the richer venue seed — ~49 venues across
Massachusetts (soccer bars by national-team/club affiliation, the Fan Festival,
brewery and waterfront screenings, hotels, and free municipal watch parties),
extracted from
[`data/world-cup-watch-parties.md`](./data/world-cup-watch-parties.md). The
smaller `sample_data.json` (4 venues) is kept as a minimal fixture for the test
suite. `importwatchparties` validates the payload against the Pydantic contract,
upserts every record by its natural key (idempotent), and finishes by
**materializing screening policies** (e.g. a bar's "shows every match" rule fans
out into concrete screenings across the full fixture list).

### Keeping fixtures fresh (`refreshfixtures`)

As the tournament progresses FIFA fills in the bracket — knockout placeholders
("Winner Group C") resolve to real teams, kickoff times occasionally shift.
`refreshfixtures` automates the whole chain in one idempotent, guarded step:

```bash
uv run python manage.py refreshfixtures
```

It fetches the FIFA v3 calendar API, maps + contract-validates the payload,
**sanity-checks** it (plausible match count ≥ 64), upserts teams/matches inside
a transaction, then **re-materializes every screening policy** so `by_team`
supporter venues automatically gain screenings for newly-resolved fixtures, and
logs a one-line change summary (newly-resolved fixtures, screenings created).

- **Scheduled in production:** a Render **Cron Job** (`worldcup-refresh` in
  [`render.yaml`](./render.yaml)) runs it **every 6 hours** (`0 */6 * * *`),
  sharing the API service's runtime and `DATABASE_URL`, so the live DB stays
  current between deploys.
- **Deploy fail-safe:** [`build.sh`](./build.sh) seeds from the committed
  `data/fifa_reference.json` snapshot, then runs `refreshfixtures || true` — so
  a deploy ends fully fresh when FIFA is reachable, falls back to the snapshot
  when it isn't, and a FIFA outage can **never** fail a deploy.
- **FIFA dependency + fail-safe behavior:** the undocumented FIFA endpoint is
  the only external dependency. On any fetch failure, HTTP error, or implausible
  payload the command leaves **all** data unmodified (no partial writes) and
  logs a warning. Authored venue/affiliation/policy rows are never deleted; only
  generated (`is_generated`) screenings are rebuilt by re-materialize.
- **No-downgrade guard:** the shared match upsert (used by *both* the seed
  loader and the refresh) NEVER overwrites an already-resolved
  `home_team`/`away_team` with a null/placeholder. So re-seeding from a stale
  snapshot, or a transient upstream blip that momentarily drops team data, can't
  un-resolve a knockout. Genuine resolved→different-resolved corrections and
  kickoff/stage changes still apply.
- **Freshness + staleness alerting:** each successful run stamps
  `fixtures_refreshed_at`, exposed at `GET /api/meta/` and shown as
  "Fixtures updated <when>" in the site footer. A single failed run is a quiet
  non-event (logged, data retained, exit 0). But if a run can't refresh **and**
  the last success was > 24h ago (or never), it escalates: a clearly-marked
  `log.error` ALERT line plus a non-zero exit. (The alert "channel" is a single
  log line today; a Slack/email webhook is a one-line config hook — see the
  `TODO(alerting)` comment in `refreshfixtures.py`.)

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
| `GET /api/search/`   | Typeahead | `q=<query>`, `limit` — ranked venue/team suggestions |
| `GET /api/teams/`    | —         | team list for the UI                        |
| `GET /api/meta/`     | —         | filter vocabularies for the UI              |

The header **search box** autocompletes across venue names, team/country names
and FIFA codes (e.g. `CRO`), supporter-hub clubs/teams (e.g. `Liverpool`), and
keywords in venue descriptions (e.g. `Tartan`). Selecting a venue opens its
detail page; selecting a team focuses the by-team view. Matching/ranking run in
Python over the small venue/team sets, so results are identical on SQLite and
PostgreSQL; a PostgreSQL trigram / full-text index is the documented upgrade
path if the dataset grows.

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
| `GOOGLE_PLACES_API_KEY`  | _(unset → venue images use the fallback)_     | server-only; see "Venue images"     |
| `VENUE_PHOTO_CACHE_SECONDS` | `86400`                                  | client/CDN cache TTL for the photo proxy redirect |

### Venue images (rights-safe)

Each venue exposes a single `image` object in the API — `{ url, attribution, source }` —
resolved over a **three-tier chain**:

1. **Confirmed Google photo** (`source: "google_places"`). When a venue has been
   resolved to a Google `place_id` *and confirmed*, its `image.url` points at the
   backend **photo proxy** (`GET /api/venues/<slug>/photo`). The proxy keeps
   `GOOGLE_PLACES_API_KEY` server-side, resolves the current Google Places photo,
   and **302-redirects** to it (`attribution` set). We **never store photo bytes** —
   only the `place_id` (which Google's terms permit long-term) and the attribution
   text. The proxy sets a long `Cache-Control` (default 24h,
   `VENUE_PHOTO_CACHE_SECONDS`) on the redirect to bound per-photo cost; it caches
   the *redirect*, not the bytes.
2. **Wikimedia Commons photo** (`source: "wikimedia"`). For public places not
   confirmed on the Google tier, a **CC-licensed Commons image** is stored as a
   stable `image_url` + attribution. Commons needs no API key, so this tier is
   always-on, but it **fails closed** (any error / no free-licensed hit → next tier).
   All Commons access is isolated in `events/wikimedia.py`.
3. **Category fallback** (`source: "fallback"`, `attribution: null`). When neither
   photo source yields an image (or the key is unset / a lookup fails), `image` is a
   clean, rights-free **category illustration** keyed by `venue_type`
   (`/venue-fallbacks/<type>.png`). It is deliberately non-photographic so it never
   implies it's a real photo of the venue. Regenerate with
   `python scripts/make_venue_fallbacks.py` (requires `rsvg-convert`).

The frontend renders the **attribution caption** whenever it is present (both photo
sources), and swaps to the category fallback on any image load error.

> **Stock imagery (e.g. Unsplash) was considered and rejected** — a generic stock
> photo misrepresents the *specific* venue, so the honest illustration is preferred.
- **Lists/cards/map pins** use the fallback only — there is **no per-row photo
  proxy call**; the full photo loads on the **detail view** only.
- **No key configured?** The feature degrades cleanly: every venue shows the
  fallback, the proxy redirects to the fallback, and nothing errors.

**Backfill — resolve venues to `place_id`s:**

```bash
# set GOOGLE_PLACES_API_KEY first (a Places API (New) enabled key)
uv run python manage.py resolvevenueplaces            # resolve unresolved venues
uv run python manage.py resolvevenueplaces --refresh   # re-resolve resolved ones
uv run python manage.py resolvevenueplaces --dry-run    # report only, write nothing
```

`resolvevenueplaces` matches each venue by name + address/city via Google Places
Text Search, stores a **confident** match's `place_id` + `image_source`, and
flags **low-confidence/ambiguous** matches with `needs_review=True` rather than
trusting a guess. It is **idempotent** — already-resolved venues are skipped unless
`--refresh` — and **no-ops without the API key**. All Google access is isolated in
`events/places.py`.

**Confirm/reject flagged candidates.** Ambiguous matches keep a candidate
`place_id` but leave `image_source` blank, so they stay on the next tier until a
reviewer decides. Either in the **admin** (multi-select the `needs_review` venues
and run the "Confirm Google photo match" / "Reject match" actions) or via the CLI:

```bash
uv run python manage.py resolvevenueplaces --confirm <slug> [<slug> ...]  # promote
uv run python manage.py resolvevenueplaces --reject  <slug> [<slug> ...]  # discard → next tier
```

`--confirm` sets `image_source="google_places"`, resolves+stores the attribution
(no-ops cleanly without the key — attribution stays blank, the proxy re-resolves
the URL), and clears `needs_review`. `--reject` clears the candidate `place_id` +
`needs_review`, dropping the venue to the next tier.

**Backfill — Wikimedia Commons (tier 2):**

```bash
uv run python manage.py resolvevenuewikimedia            # resolve eligible venues
uv run python manage.py resolvevenuewikimedia --refresh   # re-resolve wikimedia ones
uv run python manage.py resolvevenuewikimedia --dry-run    # report only, write nothing
```

For venues **not** confirmed on the Google tier, `resolvevenuewikimedia` queries
Wikimedia Commons for a **free-licensed** photo and, on a confident hit, stores
`image_url` + `image_attribution` + `image_source="wikimedia"`. It is **idempotent**
(skips google/wikimedia venues unless `--refresh`, never overwrites a confirmed
Google photo), **needs no API key**, and **fails closed** (no hit / any error →
the venue stays on the category fallback).

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
`CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `GOOGLE_PLACES_API_KEY`
(declared as a `sync: false` secret on `worldcup-api` — set it in the Render
dashboard; leave it unset to ship venue images as the category fallback).
`ALLOWED_HOSTS` /
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
