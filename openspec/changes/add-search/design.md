## Context

The app has three filtered projections of `Screening` but no direct lookup. The data is small and lives in `Venue`, `Team`, and `VenueAffiliation` (see `events/models.py`). There is no description field on `Team`; the "keyword" surface is `Venue.notes` and `VenueAffiliation.club`/`note`. The frontend already has a single URL-synced state object (`useFilters.ts`) with `view`, `venue`, and the filter set, and selecting a result just means setting that state. Constraint: must work on both SQLite (dev) and PostgreSQL (prod) without per-backend branches, and stay fast as a typeahead.

## Goals / Non-Goals

- **Goals:** one endpoint that returns ranked, typed suggestions; a debounced, keyboard-navigable header search box; selection routes into existing views; fast at current scale; dev/prod parity.
- **Non-goals:** full-text/relevance engines, fuzzy/typo-tolerant matching, searching match fixtures or free-text across screenings, paginating results, and search analytics.

## Decisions

### One typed-suggestion endpoint, not per-type endpoints
`GET /api/search/?q=` returns a single ranked list of heterogeneous suggestions (`{type, label, sublabel, target}`) rather than separate venue/team calls. The client renders one dropdown and doesn't orchestrate multiple requests per keystroke. `target` is a small directive the client already knows how to apply:
- venue → `{kind: "venue", slug}` → open `VenueDetail`
- team → `{kind: "team", code}` → set `team` filter + `view = "team"`

### Match surfaces and ranking
Searchable fields: `Venue.name`, `Venue.city`, `Venue.notes`; `Team.name`, `Team.fifa_code`; `VenueAffiliation.club` and affiliated team name. Ranking tiers (highest first): exact/prefix match on a name or code → whole-word match on a name → substring match in a name → substring match in a description/notes. Within a tier, order by name. This puts "The Haven" and "Croatia" above venues that merely mention them in prose. Results are capped (default 10).

### Case-insensitive `icontains`, backend-agnostic
At ~150 venues / 48 teams, `__icontains` (and `__istartswith` for the prefix tier) over a handful of fields is sub-millisecond and behaves the same on SQLite and PostgreSQL. Ranking is computed in Python after a small candidate fetch, keeping the query portable. **Future upgrade path (documented, not built):** PostgreSQL `pg_trgm` + `GIN` index or `SearchVector`/`SearchRank` for typo tolerance and larger corpora, guarded by `settings.USING_POSTGRES` like the family-friendly filter already is.

### Debounced typeahead, abortable
The client debounces input (~150 ms) and aborts the in-flight request on the next keystroke (`AbortController`) so out-of-order responses can't clobber the list. Empty/short queries (<2 chars) don't hit the network. Keyboard: ↑/↓ to move, Enter to select, Esc to dismiss.

### Selection reuses URL-synced state
No new routing layer: selecting a suggestion calls the existing `openVenue(slug)` or `setFilter("team", code)` + `setView("team")` from `useFilters`, so a searched result is bookmarkable/shareable for free and behaves identically to navigating by hand.

## Risks / Trade-offs

- **Python-side ranking** loads a small candidate set per query; fine at this scale, revisit if the corpus grows (the trgm path covers that).
- **Substring (`icontains`) is not typo-tolerant** — acceptable for v1; called out as the main reason to adopt trigram later.
- **Combining results from three models** means ranking lives in code, not SQL; kept simple and unit-tested to stay predictable.

## Migration Plan

Additive: new endpoint + new UI. No migrations, no changes to existing endpoints or state shape (only new fields/handlers on the existing state object). Ships behind no flag; if the box is hidden, the rest of the app is unchanged.

## Open Questions

- Should team suggestions also offer the "supporter hub" sense (set `team_mode=hub`) as a distinct result, or only the default "playing" sense? (Lean: default to playing; the by-team view already toggles the sense.)
- Minimum query length — 2 vs 3 chars (lean 2, since `fifa_code` is 3 and city/team prefixes are short).
