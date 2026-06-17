## Why

The initial search matched names, codes, and description keywords by case-insensitive **substring**. Two real gaps surfaced in review:

1. **Official names ≠ everyday names.** FIFA's data uses official short forms — "USA", "Türkiye", "Côte d'Ivoire", "Korea Republic". Typing "united states" returned *No matches*, because it shares no characters with "USA". A similarity/fuzzy match can't bridge that gap (zero overlap); it needs a **synonym/alias** map.
2. **Typos and near-misses.** "croatica", "banshe", "liverpol", "scotand" returned nothing, even though the intended target is obvious. Substring matching is unforgiving of a single wrong/missing letter.

## What Changes

- Add a **team alias map** (common name → FIFA code) for teams whose official FIFA name differs from what people type: united states→USA, turkey→Türkiye, ivory coast→Côte d'Ivoire, south korea→Korea Republic, iran, cape verde, dr congo, holland, saudi arabia. Alias prefix matches rank with name prefixes; alias substrings rank one tier below.
- Add a **typo-tolerant fuzzy fallback** using the standard library (`difflib`, no new dependency): when nothing matches by prefix/word/substring, a similarity pass over venue names, team names + aliases, and supporter-hub (club / affiliated team) names returns close matches. It is **gated to queries ≥ 4 characters** and ranked **below all exact and substring matches**, so normal queries are unaffected.
- Keep matching **backend-agnostic** (pure Python over the small dataset), so SQLite and PostgreSQL stay identical.

## Capabilities

### New Capabilities
<!-- None — this refines the existing `search` capability. -->

### Modified Capabilities
- `search`: add common-name aliases for teams and a typo-tolerant fuzzy fallback on top of the existing substring matching, without changing the response shape or the existing ranking of exact/substring matches.

## Impact

- **Code:** `events/search.py` (alias map, `difflib` fuzzy pass, ranking tier 4); no API shape change, no schema change, no new dependency.
- **Tests:** alias resolution (united states→USA, turkey→Türkiye) and fuzzy matches (team + venue typos).
- **Performance:** unchanged in practice — fuzzy runs only as a fallback over ~150 venues / 48 teams; PostgreSQL trigram/full-text remains the documented upgrade path at larger scale.
