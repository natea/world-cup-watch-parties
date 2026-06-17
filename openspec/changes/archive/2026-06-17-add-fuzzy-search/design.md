## Context

`search` (the typeahead capability) matches venue/team names, FIFA codes, supporter-hub clubs, and description keywords by case-insensitive substring, ranked in tiers (prefix → whole-word → substring → description). Two failure modes appeared in review, with different root causes that need different fixes.

## Goals / Non-Goals

**Goals:**
- Resolve common everyday team names to teams with official short FIFA names.
- Tolerate typos / near-misses without surfacing noise on normal queries.
- Stay dependency-free and identical across SQLite and PostgreSQL.

**Non-Goals:**
- Full-text / trigram search (still the documented future upgrade at larger scale).
- Phonetic matching, multilingual synonyms, or a general thesaurus.
- Changing the response shape or the ordering of existing exact/substring matches.

## Decisions

**Aliases, not fuzzy, for synonym gaps.** "united states" → "USA" has ~0 character similarity, so any edit-distance/`difflib` score is far below threshold — fuzzy fundamentally cannot solve it. A small curated `TEAM_ALIASES` map keyed by FIFA code is the correct, deterministic fix. Aliases participate in the existing tiers: an alias prefix ranks at the name-prefix tier (0), an alias substring at tier 1. Alternative considered: rename teams to common names — rejected, because the official name is the correct display value and renaming would fight the authoritative FIFA reference data.

**Fuzzy as a gated, lowest-priority fallback.** Implemented with stdlib `difflib.SequenceMatcher` (no new dependency) over the small candidate set. It only runs when a candidate has no prefix/word/substring/description match, is gated to queries ≥ 4 chars (short queries are too ambiguous to fuzz), and lands in a new tier **4** below description matches — so exact and substring results always win. Fuzzy targets include venue names, team names + aliases, and supporter-hub names (so a typo'd club like "liverpol" still finds the Liverpool bars). Alternative considered: RapidFuzz — rejected to avoid a dependency at this scale.

**Threshold.** A similarity ratio ≥ 0.8 against the whole string or any word of length ≥ 3. Tuned so single-character typos match while unrelated queries do not.

## Risks / Trade-offs

- **Fuzzy false positives** → mitigated by the 0.8 threshold, the ≥4-char gate, and tier-4 placement (only shows when nothing better matches). [Risk] a contrived query could surface a weak match → it appears last, never above a real hit.
- **Alias map drift** → it is small and only needed for teams whose FIFA name differs from common usage; easy to extend, and a miss degrades to "no alias" (substring/fuzzy still apply).

## Migration Plan

Pure additive logic in `events/search.py`; no data or schema change. Ships in the same PR as the base search feature.
