## Why

The only ways to find a place today are the three filtered views (schedule, map, by-team). There's no way to jump straight to a venue you already have in mind ("The Haven", "Tartan Army"), to a country/team ("Croatia", "CRO"), or to a fuzzy idea ("rooftop", "brewery", "Scottish pub"). Users have to eyeball long lists. A single search box that autocompletes as you type — across venue names, team/country names, and keywords in venue/affiliation descriptions — is the fastest path to the thing someone wants, and it complements (doesn't replace) the existing filters.

## What Changes

- Add a **`GET /api/search/?q=<query>` endpoint** returning ranked, typed suggestions across:
  - **Venues** — match on `name`, `city`, and `notes`.
  - **Teams / countries** — match on `Team.name` and `fifa_code` (e.g. "CRO").
  - **Supporter hubs / clubs** — match on `VenueAffiliation.club` and affiliated team name (e.g. "Tartan Army" → The Haven).
- Each suggestion carries a **type**, a display **label** + **sublabel**, and a **target** describing what selecting it does: open a venue's detail (`venue` slug), or focus a team (set the `team` filter + switch to the by-team view).
- **Ranking** favors prefix/whole-word matches on names over substring matches in descriptions, so the most likely hit is first; results are **capped** (e.g. 10) for a tight autocomplete list.
- Add a **search box in the app header** with debounced typeahead, a keyboard-navigable dropdown, and selection that routes to the right view via the existing `view`/`venue`/filter state (URL-synced).
- Keep it **backend-agnostic and fast**: case-insensitive matching that runs on both SQLite (dev) and PostgreSQL (prod) at the current dataset size, with Postgres trigram/full-text noted as a future upgrade path rather than a requirement.

## Capabilities

### New Capabilities
- `search`: a typeahead search endpoint and header UI that finds venues, teams/countries, and supporter hubs by name or by keywords in their descriptions, returning ranked typed suggestions that route into the existing views.

### Modified Capabilities
<!-- The build-watch-party-v1 change (screening-api, web-client) is not yet archived, so its specs are not in openspec/specs/. The new behavior is captured as ADDED requirements under the new `search` capability. -->

## Impact

- **New code:** a `SearchView` (`events/views.py`) + URL (`events/urls.py`); a small suggestion serializer; a `SearchBox` component (`frontend/src/components/`) wired into `App.tsx` and the shared filter/view state (`useFilters.ts`).
- **No schema changes** — search reads existing `Venue`, `Team`, and `VenueAffiliation` fields.
- **Performance:** queries are limited and indexed on the fields already used; acceptable at ~150 venues / 48 teams. Trigram/full-text is a documented future option, not in scope.
- **Tests:** endpoint ranking/typing/limit behavior and the dev (SQLite) matching path.
