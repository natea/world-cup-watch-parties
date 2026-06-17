## Context

The watch-party finder seeds reference data (teams + fixtures) separately from venue data, on purpose: fixtures are correctness-critical and must come from an authoritative source, never an LLM (PRD §9.1). v1 shipped with only the 7 Gillette fixtures, hand-entered with **provisional** match numbers (the research guide gave matchups + kickoffs but not canonical FIFA numbers). Consequently every non-Gillette nation has no matches, and venues with `by_team` policies for those nations (Blackmoor→Croatia, Fogo→Brazil) materialize zero screenings and vanish from all views.

The canonical schedule is published at FIFA.com but only via an undocumented internal API. We obtained the exact call by reverse-engineering the site's network traffic — the technique libretto is built for. Here it was done with the **Playwright MCP server** (which libretto itself wraps): load the fixtures page, list the captured XHRs, and identify the data call among them.

### What the reverse-engineering found

- **Endpoint:** `GET https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=285023`
- **Identifiers:** `idCompetition=17` (men's World Cup), `idSeason=285023` (2026). Stages list at `…/api/v3/stages?idSeason=285023`.
- **Payload:** `{ Results: [ … 104 matches … ] }`. Per match: `MatchNumber`, `Date` (UTC), `LocalDate`, `Home`/`Away` (each with `IdCountry` 3-letter code, `TeamName`, `Abbreviation`; null for unresolved knockouts), `StageName`, `GroupName`, `Stadium`, `PlaceHolderA`/`PlaceHolderB`.
- **Confirmed:** 104 matches, 48 teams (USA/BRA/CRO present), 3-letter codes that match our `Team.fifa_code`. The 7 "Boston Stadium" matches carry real numbers 5, 18, 30, 45, 61, 74, 97 — same matchups/kickoffs as our provisional 22, 40, 54, 63, 71, 88, 99.

## Goals / Non-Goals

**Goals:**
- A repeatable fetch of the authoritative 104-match list into the existing reference-data contract.
- A committed offline snapshot so routine seeding never depends on a live, undocumented endpoint.
- Reconcile the prior provisional Gillette numbers so existing `specific` watch-party policies stay correct.
- Light up every nation's "playing" view and `by_team` supporter bars.

**Non-Goals:**
- Live scores, standings, or in-match updates (the API exposes them; out of scope — this is a finder).
- A scheduled/automatic refresh job. Fetch is run on demand; the snapshot is the source of truth.
- Adding new venue data (separate concern; this change is reference data only).

## Decisions

**Fetch is a separate step from load; the snapshot is canonical.** `fetchfixtures` calls the API and writes `data/fifa_reference.json`; `loadreferencedata --path data/fifa_reference.json` loads it. Rationale: the endpoint is undocumented and may rate-limit, change, or block automated clients. Committing the snapshot keeps `migrate → loadreferencedata → importwatchparties` deterministic and offline. Alternative considered: fetch directly inside `loadreferencedata` — rejected; it couples every seed to network availability.

**Reuse the existing reference-data contract and loader.** `fetchfixtures` emits `{teams, matches}` exactly as `loadreferencedata --path` already expects, and the loader already upserts by `fifa_code`/`fifa_match_number`. No new loader, no migration. The fetch command's only job is FIFA-JSON → contract mapping.

**Field mapping.**
- `MatchNumber` → `fifa_match_number` (the stable natural key).
- `Home.IdCountry` / `Away.IdCountry` → `home_team_code` / `away_team_code` (null when the side is unresolved).
- `Date` → `kickoff` (already UTC).
- `StageName` → `stage` enum via a fixed table: First Stage→`group`, Round of 32→`r32`, Round of 16→`r16`, Quarter-final→`qf`, Semi-final→`sf`, Play-off for third place→`third`, Final→`final`.
- `GroupName` ("Group A") → `group` ("A"); empty for knockouts.
- `Stadium` → `host_stadium` (+ city → `host_city`).
- `PlaceHolderA`/`PlaceHolderB` → `home_placeholder`/`away_placeholder`; `bracket_slot` from the stage/match identity for stable re-resolution.
- Teams: one `TeamIn` per distinct `IdCountry`, name from `TeamName`.

**Provisional → real reconciliation, done once.** Replace the 7 Gillette match numbers in `data/watch_parties.json` (22→5, 40→18, 54→30, 63→45, 71→61, 88→74, 99→97) and drop the provisional fixtures from `loadreferencedata`'s built-in seed so the authoritative file is the single source. Rationale: the provisional numbers collide with real FIFA matches (real #22 is a different game); leaving them would both mis-target `specific` policies and corrupt those real fixtures on load.

## Risks / Trade-offs

- **Undocumented API may change or block automated requests.** → The committed `data/fifa_reference.json` snapshot is the canonical seed; `fetchfixtures` is only needed to refresh it. If the endpoint dies, seeding still works.
- **`idSeason` is environment-specific magic.** → Documented here and defaulted in the command, overridable via a flag, and discoverable by re-running the same network-capture technique.
- **Team-code mismatches** (FIFA `IdCountry` vs our existing codes). → Spot-checked: the codes used by affiliations (USA, BRA, CRO, FRA, SCO, ENG, GHA, IRQ, MAR, NOR, HAI) all match. The loader upserts teams, so any new codes are added, not rejected.
- **Re-materialization churn.** Changing Gillette kickoff times/numbers changes generated-screening natural keys. → Re-seed from a clean flush in dev; the importer is idempotent, so a corrected load overwrites cleanly.
- **Stale knockout resolutions.** As the real tournament progresses, placeholders resolve. → Re-running `fetchfixtures` + `loadreferencedata` + policy re-materialization picks up resolved opponents (the existing PRD §8.5 path).

## Migration Plan

1. `fetchfixtures` → write/commit `data/fifa_reference.json`.
2. Edit `data/watch_parties.json` (provisional → real Gillette numbers) and `loadreferencedata` (drop provisional seed).
3. Dev: `flush` → `loadreferencedata --path data/fifa_reference.json` → `importwatchparties data/watch_parties.json` (re-materializes policies).
4. Verify USA/BRA/CRO have matches and their bars appear. Rollback = revert the two edited files and re-seed; idempotent, no schema change.

## Open Questions

- Should the committed snapshot include only Massachusetts-relevant fields, or the full payload for future use (venues, knockout re-resolution)? Leaning: store the mapped `{teams, matches}`, not the raw FIFA blob.
- Do we want a thin `--refresh` convenience that chains fetch → load? Deferred; keep steps explicit for now.
