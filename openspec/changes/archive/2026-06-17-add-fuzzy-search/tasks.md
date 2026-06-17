## 1. Aliases

- [x] 1.1 Add `TEAM_ALIASES` (common name → FIFA code) for teams whose FIFA name is an official short form (united states, turkey, ivory coast, south korea, iran, cape verde, dr congo, holland, saudi arabia)
- [x] 1.2 Match aliases in team ranking: alias prefix → tier 0, alias substring → tier 1

## 2. Fuzzy fallback

- [x] 2.1 Add a `difflib`-based similarity helper (stdlib, no new dependency), gated to queries ≥ 4 chars, threshold ≥ 0.8 over whole string and words ≥ 3 chars
- [x] 2.2 Apply as a tier-4 fallback (below description matches) when a candidate has no prefix/word/substring/description match
- [x] 2.3 Include supporter-hub (club / affiliated team) names in venue fuzzy targets so a typo'd club still surfaces its venues

## 3. Tests & docs

- [x] 3.1 Tests: alias resolution (united states→USA, turkey→Türkiye) and fuzzy matches (team typo, venue typo)
- [x] 3.2 README/spec note: aliases + fuzzy fallback; PostgreSQL trigram/full-text remains the future upgrade path
