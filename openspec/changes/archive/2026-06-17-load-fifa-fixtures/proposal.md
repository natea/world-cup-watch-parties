## Why

The app only has the seven Gillette Stadium fixtures loaded, so the ~40 other nations — including the USA, Brazil, and Croatia, whose Boston supporter bars are already in the dataset — have **no games**. Their "where is my team playing" views are empty and their `by_team` supporter bars (which materialize zero screenings without matches) are invisible. The fix is the deferred reference-data step: load the authoritative full FIFA 2026 fixture list (104 matches, 48 teams) from FIFA's own data, replacing the hand-entered provisional fixtures.

The fixtures live behind FIFA.com's undocumented internal API. Using the libretto technique — capturing the site's network traffic to reverse-engineer its API — we identified the exact endpoint and parameters, confirmed it returns all 104 matches with stable match numbers, UTC kickoffs, FIFA 3-letter team codes (which match our `Team.fifa_code`), stadiums, and knockout placeholders.

## What Changes

- Add a `fetchfixtures` management command that calls FIFA's v3 calendar API (`api.fifa.com/api/v3/calendar/matches`, `idSeason=285023`), maps each match to the existing reference-data contract, and writes `data/fifa_reference.json` (teams + 104 matches). A committed snapshot of that file is the offline source of truth, since the endpoint is undocumented and may change.
- Map FIFA fields → our schema: `MatchNumber`→`fifa_match_number`, `IdCountry`→`fifa_code`, `Date`→UTC `kickoff`, `StageName`→`stage` enum, `GroupName`→`group`, `Stadium`→`host_city`/`host_stadium`, `PlaceHolderA/B`→placeholders (null teams for unresolved knockouts).
- Load it via the existing idempotent `loadreferencedata --path data/fifa_reference.json` (upsert by `fifa_match_number`), and remove the provisional fixtures from the built-in seed.
- **Reconcile the provisional Gillette match numbers** in `data/watch_parties.json` to the real FIFA numbers (22→5, 40→18, 54→30, 63→45, 71→61, 88→74, 99→97) so the `specific` watch-party policies keep pointing at the right games.
- Re-materialize policies so every team's matches (and their `by_team` supporter bars) populate.

## Capabilities

### New Capabilities
- `fifa-fixtures`: fetching the authoritative FIFA 2026 fixture list from the reverse-engineered FIFA API, mapping it to the reference-data contract, and reconciling the prior provisional match numbers.

### Modified Capabilities
<!-- The build-watch-party-v1 change is not yet archived, so its specs are not in openspec/specs/. The reference-data and data-import behavior touched here is captured as ADDED requirements under the new fifa-fixtures capability rather than as deltas. -->

## Impact

- **New code:** `events/management/commands/fetchfixtures.py`; a stage-name → `Stage` enum mapping.
- **New data:** `data/fifa_reference.json` (committed snapshot of the 104-match list + 48 teams).
- **Edited:** `events/management/commands/loadreferencedata.py` (drop provisional fixtures; the authoritative file becomes the seed); `data/watch_parties.json` (provisional → real Gillette match numbers).
- **External dependency:** FIFA's undocumented `api.fifa.com/api/v3` endpoint — used at fetch time only; the committed snapshot insulates routine seeding from API drift/outage.
- **Result:** all 48 nations have fixtures; the team "playing" view and `by_team` supporter bars light up tournament-wide.
