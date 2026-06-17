## 1. Fetch command

- [ ] 1.1 Add `events/management/commands/fetchfixtures.py` calling `api.fifa.com/api/v3/calendar/matches?count=500&idSeason=<season>` (default season 285023, `--season` override, `--out data/fifa_reference.json`)
- [ ] 1.2 Map FIFA match → contract: `MatchNumber`→`fifa_match_number`, `Date`→UTC `kickoff`, `Home/Away.IdCountry`→team codes (null for unresolved), `Stadium`→`host_city`/`host_stadium`, `PlaceHolderA/B`→placeholders
- [ ] 1.3 Stage-name → `Stage` enum table (First Stage→group, Round of 32→r32, Round of 16→r16, Quarter-final→qf, Semi-final→sf, third place→third, Final→final); `GroupName`→single-letter `group`; derive a stable `bracket_slot` for knockouts
- [ ] 1.4 Emit one `TeamIn` per distinct `IdCountry` (name from `TeamName`); validate the whole bundle against the import contract before writing

## 2. Snapshot & reference load

- [ ] 2.1 Run `fetchfixtures` and commit `data/fifa_reference.json` (104 matches, 48 teams) as the canonical offline seed
- [ ] 2.2 Load via `loadreferencedata --path data/fifa_reference.json`; confirm idempotent re-run and timezone-aware kickoffs

## 3. Reconcile provisional numbers

- [ ] 3.1 In `data/watch_parties.json`, remap Gillette match numbers in `specific` policies: 22→5, 40→18, 54→30, 63→45, 71→61, 88→74, 99→97
- [ ] 3.2 Remove the provisional Gillette fixtures from `loadreferencedata`'s built-in seed so the authoritative file is the single source (keep teams that affiliations need if not in the FIFA list)

## 4. Re-seed & verify

- [ ] 4.1 Dev re-seed: `flush` → `loadreferencedata --path data/fifa_reference.json` → `importwatchparties data/watch_parties.json` (re-materializes policies)
- [ ] 4.2 Verify USA/Brazil/Croatia now have matches in the "playing" query and their `by_team` bars (Banshee, Fogo, Blackmoor) have materialized screenings
- [ ] 4.3 Verify the 7 Gillette matches exist once each under their real numbers with correct matchups/kickoffs, and `specific` policies (Lawn on D, Lucky Strike, Davio's, community parties) point at the right games

## 5. Tests & docs

- [ ] 5.1 Test the FIFA→contract mapping on a committed sample of the payload (resolved group match, unresolved knockout, stage/group parsing) without hitting the network
- [ ] 5.2 Test that loading the snapshot yields 104 matches / 48 teams and that a non-Gillette nation has ≥1 screening after materialization
- [ ] 5.3 Update the README seed flow to load `data/fifa_reference.json`, and document the `fetchfixtures` refresh step + the reverse-engineered endpoint/`idSeason`
